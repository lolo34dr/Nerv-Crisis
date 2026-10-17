import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from collections import defaultdict
import unittest
import pygame
from engine.game.shooter import Game


class GameTests(unittest.TestCase):
    def setUp(self):
        self.game = Game(seed=1)
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.keys = defaultdict(bool)

    def tearDown(self):
        pygame.quit()

    def test_movement_and_shooting(self):
        self.keys[pygame.K_SPACE] = True
        self.keys[pygame.K_LEFT] = True
        start = self.game.player.x
        self.game.update(.05, self.keys)
        self.assertLess(self.game.player.x, start)
        self.assertEqual(len(self.game.bullets), 1)
        for _ in range(100):
            self.game.update(.05, self.keys)
        self.assertGreaterEqual(self.game.player.x, 20)

    def test_hit_scores_and_removes_enemy(self):
        self.game.enemies = [pygame.Vector2(100, 100)]
        self.game.bullets = [pygame.Vector2(100, 100)]
        self.game.update(0, self.keys)
        self.assertEqual(self.game.score, 100)
        self.assertEqual(self.game.enemies, [])
        self.assertEqual(self.game.bullets, [])

    def test_damage_protection_gameover_and_restart(self):
        self.game.enemies = [self.game.player.copy(), self.game.player.copy()]
        self.game.update(0, self.keys)
        self.assertEqual(self.game.lives, 2)
        for _ in range(2):
            self.game.invulnerable = 0
            self.game.enemies = [self.game.player.copy()]
            self.game.update(0, self.keys)
        self.assertEqual(self.game.state, 'gameover')
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(self.game.state, 'playing')
        self.assertEqual(self.game.lives, 3)

    def test_pause_freezes_world_and_focus_loss_pauses(self):
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p))
        self.game.update(1, self.keys)
        self.assertEqual(self.game.elapsed, 0)
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p))
        self.game.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertEqual(self.game.state, 'paused')

    def test_progression_render_and_quit(self):
        self.game.elapsed = 40
        self.assertEqual(self.game.level, 3)
        for state in ('menu', 'playing', 'paused', 'gameover'):
            self.game.state = state
            self.game.draw()
        self.game.handle_event(pygame.event.Event(pygame.QUIT))
        self.assertFalse(self.game.running)


if __name__ == '__main__':
    unittest.main()
