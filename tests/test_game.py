import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from collections import defaultdict
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import pygame
from engine.game.shooter import Game, Enemy, Shot, Pickup, ARENA, SIZE


class GameTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((1, 1))
        self.game = Game(pygame.Surface(SIZE), seed=1)
        self.game.invulnerable = 0
        self.keys = defaultdict(bool)

    def tearDown(self):
        pygame.quit()

    def test_game_never_owns_display_or_audio(self):
        with patch('pygame.display.set_mode') as window, patch('pygame.mixer.music.load') as music:
            game = Game(pygame.Surface(SIZE))
            game.draw()
        window.assert_not_called()
        music.assert_not_called()

    def test_movement_shooting_and_bounds(self):
        self.keys[pygame.K_SPACE] = True
        self.keys[pygame.K_LEFT] = True
        start = self.game.player.x
        self.game.update(.05, self.keys)
        self.assertLess(self.game.player.x, start)
        self.assertEqual(len(self.game.bullets), 1)
        for _ in range(100):
            self.game.update(.05, self.keys)
        self.assertGreaterEqual(self.game.player.x, ARENA.left + 22)

    def test_hit_scores_and_armored_enemy_takes_multiple_hits(self):
        enemy = Enemy(pygame.Vector2(200, 220), 'gunner', 3)
        self.game.enemies = [enemy]
        for expected in (2, 1, 0):
            self.game.bullets.append(Shot(enemy.pos.copy(), pygame.Vector2(0, -640)))
            self.game.update(0, self.keys)
            self.assertEqual(enemy.hp, expected)
        self.assertEqual(self.game.score, 250)
        self.assertEqual(self.game.kills, 1)
        self.assertFalse(self.game.enemies)

    def test_damage_shields_invulnerability_and_gameover(self):
        self.game.shield = 1
        self.game.damage()
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.shield, 0)
        self.game.damage()
        self.assertEqual(self.game.lives, 3)
        for _ in range(3):
            self.game.invulnerable = 0
            self.game.damage()
        self.assertEqual(self.game.state, 'gameover')
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(self.game.state, 'playing')
        self.assertEqual(self.game.lives, 3)

    def test_enemies_leaking_damage_base_not_player(self):
        self.game.enemies = [Enemy(pygame.Vector2(200, ARENA.bottom + 50))]
        self.game.update(0, self.keys)
        self.assertEqual(self.game.base, 90)
        self.assertEqual(self.game.lives, 3)
        self.game.base = 10
        self.game.enemies = [Enemy(pygame.Vector2(200, ARENA.bottom + 50))]
        self.game.update(0, self.keys)
        self.assertEqual(self.game.state, 'gameover')

    def test_pause_and_focus_loss_freeze_all_timers(self):
        self.game.rapid = 5
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p))
        self.game.update(1, self.keys)
        self.assertEqual(self.game.elapsed, 0)
        self.assertEqual(self.game.rapid, 5)
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p))
        self.game.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertEqual(self.game.state, 'paused')

    def test_pickups_rapid_spread_heal_and_expiration(self):
        for kind in ('rapid', 'spread', 'heal', 'shield'):
            self.game.pickups.append(Pickup(self.game.player.copy(), kind))
        self.game.update(0, self.keys)
        self.assertEqual(self.game.lives, 4)
        self.assertEqual(self.game.shield, 1)
        self.assertEqual(self.game.bonuses, 4)
        self.keys[pygame.K_SPACE] = True
        self.game.update(.01, self.keys)
        self.assertEqual(len(self.game.bullets), 3)
        self.assertEqual(self.game.shot_timer, .085)
        self.game.rapid = self.game.spread = .01
        self.game.update(.05, self.keys)
        self.assertEqual(self.game.rapid, 0)
        self.assertEqual(self.game.spread, 0)

    def test_dash_cooldown_and_pulse_damage_boss(self):
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LSHIFT)
        self.game.handle_event(event)
        self.assertGreater(self.game.invulnerable, 0)
        self.game.dash_timer = 0
        self.game.handle_event(event)
        self.assertEqual(self.game.dash_timer, 0)
        boss = self.game.spawn('boss')
        hp = boss.hp
        self.game.hostile_shots.append(Shot(self.game.player.copy(), pygame.Vector2()))
        self.game.bomb()
        self.assertEqual(self.game.energy, 0)
        self.assertEqual(boss.hp, hp - 12)
        self.assertFalse(self.game.hostile_shots)
        self.game.bomb()
        self.assertEqual(boss.hp, hp - 12)

    def test_wave_five_spawns_boss_and_defeat_rewards(self):
        self.game.wave = 4
        self.game.spawn_remaining = 0
        self.game.wave_timer = 2.49
        self.game.update(.05, self.keys)
        self.assertEqual(self.game.wave, 5)
        self.assertEqual(self.game.enemies[0].kind, 'boss')
        boss = self.game.enemies[0]
        boss.pos.y = ARENA.top + 130
        boss.shot_timer = 0
        self.game.update(.01, self.keys)
        self.assertEqual(len(self.game.hostile_shots), 5)
        self.game.hostile_shots.clear()
        boss.hp = 20
        boss.shot_timer = 0
        self.game.update(.01, self.keys)
        self.assertEqual(len(self.game.hostile_shots), 7)
        self.game.base = 60
        self.game.kill(boss)
        self.assertEqual(self.game.bosses_defeated, 1)
        self.assertEqual(self.game.base, 80)
        self.assertEqual(self.game.pickups[-1].kind, 'heal')

    def test_combo_and_guaranteed_bonus_drop(self):
        for _ in range(5):
            self.game.kill(self.game.spawn('scout'))
        self.assertEqual(self.game.score, 900)
        self.assertEqual(len(self.game.pickups), 1)
        self.game.combo_timer = .01
        self.game.update(.05, self.keys)
        self.assertEqual(self.game.combo, 0)

    def test_snapshot_roundtrip_and_corrupt_data_is_atomic(self):
        self.game.wave = 5
        self.game.spawn('boss')
        self.game.score = 3450
        self.game.rapid = 8
        self.game.shield = 2
        self.game.spawn_remaining = 0
        self.game.bullets.append(Shot(self.game.player.copy(), pygame.Vector2(0, -640)))
        data = json.loads(json.dumps(self.game.snapshot()))
        restored = Game(self.game.screen)
        restored.restore(data)
        self.assertEqual(restored.snapshot(), data)
        self.assertEqual(restored.state, 'paused')
        for field, value in (('lives', -1), ('wave', float('nan')), ('enemies', [{}]),
                             ('player', [0, 0]), ('hostile_shots', [{}] * 501)):
            bad = deepcopy(data)
            bad[field] = value
            with self.assertRaises(ValueError):
                restored.restore(bad)
            self.assertEqual(restored.snapshot(), data)

    def test_long_simulation_saves_and_renders_all_states(self):
        self.game.autofire = True
        self.keys[pygame.K_RIGHT] = True
        for _ in range(1200):
            self.game.invulnerable = 1
            self.game.base = 100
            self.game.update(.05, self.keys)
        restored = Game(self.game.screen)
        restored.restore(self.game.snapshot())
        for kind in ('scout', 'zigzag', 'gunner', 'boss'):
            enemy = self.game.spawn(kind)
            enemy.pos = pygame.Vector2(200 + len(self.game.enemies) * 80, 300)
        for state in ('playing', 'paused', 'gameover'):
            self.game.state = state
            self.game.draw()

    def test_objective_reward_only_once_and_old_save_compatibility(self):
        for _ in range(5):
            self.game.kill(self.game.spawn('scout'))
        self.assertTrue(self.game.objective_done)
        self.assertEqual(self.game.objectives_completed, 1)
        score = self.game.score
        self.game.check_objective('kill')
        self.assertEqual(self.game.score, score)
        current = self.game.snapshot()
        restored = Game(self.game.screen)
        restored.restore(current)
        self.assertEqual(restored.objectives_completed, 1)
        self.assertTrue(restored.objective_done)
        old = dict(current)
        for key in ('objectives_completed', 'objective_progress', 'objective_done', 'wave_breached'):
            del old[key]
        restored.restore(old)
        self.assertEqual(restored.objectives_completed, 0)
        self.assertEqual(restored.score, current['score'])

    def test_defense_objective_fails_after_a_base_breach(self):
        self.game.wave = 3
        self.game.wave_breached = True
        self.game.check_objective('clear')
        self.assertFalse(self.game.objective_done)
        self.game.wave_breached = False
        self.game.check_objective('clear')
        self.assertTrue(self.game.objective_done)
        self.game.next_wave()
        self.assertFalse(self.game.objective_done)
        self.assertEqual(self.game.objective_progress, 0)

    def test_supply_objective_completes_on_collection(self):
        self.game.wave = 2
        self.game.collect(Pickup(self.game.player.copy(), 'energy'))
        self.assertTrue(self.game.objective_done)
        self.assertEqual(self.game.objectives_completed, 1)


if __name__ == '__main__':
    unittest.main()
