"""Arcade combat scene. The application owns the window, audio and event loop."""
from dataclasses import dataclass
import math
import random

import pygame

from .storage import DIFFICULTIES
from .assets import CombatAssets

SIZE = (1280, 800)
ARENA = pygame.Rect(36, 108, 872, 640)
CYAN = (92, 232, 210)
PINK = (241, 112, 172)
GOLD = (255, 198, 99)
TEXT = (229, 238, 243)
MUTED = (143, 165, 182)
ENEMY_STATS = {'scout': (1, 19, 130, 100), 'zigzag': (2, 23, 100, 180),
               'gunner': (3, 26, 65, 250), 'boss': (70, 65, 20, 2500)}
PICKUPS = {'heal': ('+', PINK), 'shield': ('S', CYAN), 'rapid': ('R', GOLD),
           'spread': ('T', (178, 155, 255)), 'energy': ('E', (120, 200, 255))}


@dataclass
class Enemy:
    pos: pygame.Vector2
    kind: str = 'scout'
    hp: int = 1
    age: float = 0
    shot_timer: float = 1.5

    @property
    def radius(self):
        return ENEMY_STATS[self.kind][1]


@dataclass
class Shot:
    pos: pygame.Vector2
    velocity: pygame.Vector2


@dataclass
class Pickup:
    pos: pygame.Vector2
    kind: str


class Game:
    def __init__(self, surface, seed=None, difficulty='normal', best=0, effects=True, assets=None):
        self.screen = surface
        self.rng = random.Random(seed)
        self.difficulty = difficulty
        self.factor = DIFFICULTIES[difficulty]
        self.best = best
        self.effects = effects
        self.assets = assets or CombatAssets.load()
        self.font = self.assets.font
        self.small = self.assets.small
        self.title_font = self.assets.title
        self.art = self.assets.art
        self.stars = [(self.rng.randrange(ARENA.left, ARENA.right),
                       self.rng.randrange(ARENA.top, ARENA.bottom), self.rng.uniform(12, 55)) for _ in range(75)]
        self.pause_rects = [pygame.Rect(284, 300 + i * 66, 376, 52) for i in range(4)]
        self.reset()

    def reset(self):
        self.player = pygame.Vector2(ARENA.centerx, ARENA.bottom - 65)
        self.bullets = []
        self.hostile_shots = []
        self.enemies = []
        self.pickups = []
        self.particles = []
        self.score = 0
        self.lives = 5 if self.difficulty == 'cadet' else 3
        self.base = 100
        self.elapsed = 0.0
        self.wave = 1
        self.spawn_remaining = 7
        self.spawn_timer = 1.0
        self.wave_timer = 0.0
        self.shot_timer = 0.0
        self.invulnerable = 1.5
        self.dash_timer = 0.0
        self.dash_cooldown = 0.0
        self.shield = 0
        self.rapid = 0.0
        self.spread = 0.0
        self.energy = 100.0
        self.pulse = 0.0
        self.combo = 0
        self.combo_timer = 0.0
        self.kills = 0
        self.bosses_defeated = 0
        self.bonuses = 0
        self.objectives_completed = 0
        self.objective_progress = 0
        self.objective_done = False
        self.wave_breached = False
        self.autofire = False
        self.state = 'playing'
        self.selected = 0
        self.banner = 'MISSION / DEFEND TOKYO-3'
        self.banner_timer = 3.0
        self.reported = False

    def message(self, text):
        self.banner = text
        self.banner_timer = 2.5

    @property
    def objective_kind(self):
        return 'angel' if self.wave % 5 == 0 else ('hunt', 'supply', 'defend')[(self.wave - 1) % 3]

    @property
    def objective_target(self):
        return 5 if self.objective_kind == 'hunt' else 1

    def check_objective(self, event):
        if self.objective_done:
            return
        kind = self.objective_kind
        if ((kind == 'hunt' and event == 'kill') or
                (kind == 'supply' and event == 'pickup') or
                (kind == 'angel' and event == 'boss') or
                (kind == 'defend' and event == 'clear' and not self.wave_breached)):
            self.objective_progress += 1
        if self.objective_progress >= self.objective_target:
            self.objective_done = True
            self.objectives_completed += 1
            reward = 250 + min(750, self.wave * 50)
            self.score += reward
            self.energy = min(100, self.energy + 20)
            self.message(f'OBJECTIVE COMPLETE / +{reward} SCORE / +20 ENERGY')

    def handle_event(self, event, position=None):
        """Return navigation actions to the host; never create or close a window."""
        if event.type == pygame.WINDOWFOCUSLOST and self.state == 'playing':
            self.state = 'paused'
            self.selected = 0
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p) and self.state in ('playing', 'paused'):
                self.state = 'paused' if self.state == 'playing' else 'playing'
                self.selected = 0
            elif self.state in ('paused', 'gameover'):
                count = 4 if self.state == 'paused' else 2
                if event.key in (pygame.K_DOWN, pygame.K_UP, pygame.K_TAB):
                    self.selected = (self.selected + (-1 if event.key == pygame.K_UP else 1)) % count
                elif event.key == pygame.K_RETURN:
                    return self.choose(self.selected)
            elif self.state == 'playing':
                if event.key == pygame.K_f:
                    self.autofire = not self.autofire
                elif event.key == pygame.K_c:
                    self.bomb()
                elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT) and self.dash_cooldown <= 0:
                    self.dash_timer = .18
                    self.dash_cooldown = 2.2
                    self.invulnerable = max(self.invulnerable, .25)
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN) and position is not None and self.state != 'playing':
            count = 4 if self.state == 'paused' else 2
            for index, rect in enumerate(self.pause_rects[:count]):
                if rect.collidepoint(position):
                    self.selected = index
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        return self.choose(index)
        return None

    def choose(self, index):
        if self.state == 'paused':
            if index == 0:
                self.state = 'playing'
            else:
                return ('settings', 'save', 'menu')[index - 1]
        elif self.state == 'gameover':
            if index == 0:
                self.reset()
            else:
                return 'menu'
        return None

    def burst(self, position, color):
        if not self.effects:
            return
        for _ in range(12):
            angle = self.rng.uniform(0, math.tau)
            velocity = pygame.Vector2(math.cos(angle), math.sin(angle)) * self.rng.uniform(45, 170)
            self.particles.append([pygame.Vector2(position), velocity, .5, color])
        self.particles = self.particles[-400:]

    def damage(self):
        if self.invulnerable > 0 or self.state != 'playing':
            return
        if self.shield:
            self.shield -= 1
            self.message('SHIELD / IMPACT ABSORBED')
        else:
            self.lives -= 1
        self.invulnerable = 1.4
        self.combo = 0
        self.combo_timer = 0
        self.burst(self.player, PINK)
        self.check_end()

    def check_end(self):
        if self.lives <= 0 or self.base <= 0:
            self.state = 'gameover'
            self.selected = 0
            self.best = max(self.best, self.score)

    def spawn(self, kind=None):
        if kind is None:
            choices = ['scout'] + (['zigzag'] if self.wave >= 2 else []) + (['gunner'] if self.wave >= 3 else [])
            kind = self.rng.choice(choices)
        hp = ENEMY_STATS[kind][0] + (self.wave // 5 if kind != 'boss' else self.wave * 2)
        pos = pygame.Vector2(ARENA.centerx if kind == 'boss' else self.rng.randrange(ARENA.left + 50, ARENA.right - 50), ARENA.top - 70)
        enemy = Enemy(pos, kind, hp)
        self.enemies.append(enemy)
        return enemy

    def kill(self, enemy):
        if enemy not in self.enemies:
            return
        self.enemies.remove(enemy)
        self.kills += 1
        self.combo += 1
        self.combo_timer = 3.0
        multiplier = min(5, 1 + self.combo // 5)
        self.score += ENEMY_STATS[enemy.kind][3] * multiplier
        self.energy = min(100, self.energy + 8)
        self.burst(enemy.pos, GOLD)
        if enemy.kind == 'boss':
            self.bosses_defeated += 1
            self.base = min(100, self.base + 20)
            self.pickups.append(Pickup(enemy.pos.copy(), 'heal'))
            self.message('ANGEL DEFEATED / BASE +20')
        elif self.kills % 5 == 0:
            self.pickups.append(Pickup(enemy.pos.copy(), self.rng.choice(list(PICKUPS))))
        self.check_objective('boss' if enemy.kind == 'boss' else 'kill')

    def bomb(self):
        if self.energy < 100 or self.state != 'playing':
            return
        self.energy = 0
        self.pulse = .6
        self.hostile_shots.clear()
        for enemy in self.enemies[:]:
            enemy.hp -= 12
            if enemy.hp <= 0:
                self.kill(enemy)
        self.message('AT FIELD / PULSE')

    def collect(self, pickup):
        self.bonuses += 1
        if pickup.kind == 'heal':
            self.lives = min(5, self.lives + 1)
        elif pickup.kind == 'shield':
            self.shield = min(2, self.shield + 1)
        elif pickup.kind == 'rapid':
            self.rapid = 10.0
        elif pickup.kind == 'spread':
            self.spread = 10.0
        elif pickup.kind == 'energy':
            self.energy = min(100, self.energy + 40)
        self.message({'heal': 'REPAIRS / +1 LIFE', 'shield': 'SHIELD ACTIVATED',
                      'rapid': 'RAPID FIRE / 10 SECONDS', 'spread': 'TRIPLE SHOT / 10 SECONDS',
                      'energy': 'ENERGY / +40'}[pickup.kind])
        self.check_objective('pickup')

    def next_wave(self):
        self.check_objective('clear')
        self.wave += 1
        self.objective_progress = 0
        self.objective_done = False
        self.wave_breached = False
        self.base = min(100, self.base + 5)
        self.energy = min(100, self.energy + 10)
        self.wave_timer = 0
        if self.wave % 5 == 0:
            self.spawn('boss')
            self.spawn_remaining = 0
            self.message(f'WARNING / ANGEL APPROACHING / WAVE {self.wave}')
        else:
            self.spawn_remaining = min(30, 5 + self.wave * 2)
            self.spawn_timer = 1.5
            self.message(f'WAVE {self.wave} / GET READY')

    def update(self, dt, keys=None):
        if self.state != 'playing':
            return
        dt = max(0, min(dt, .05))
        keys = pygame.key.get_pressed() if keys is None else keys
        self.elapsed += dt
        for name in ('invulnerable', 'dash_timer', 'dash_cooldown', 'rapid', 'spread',
                     'pulse', 'combo_timer', 'banner_timer'):
            setattr(self, name, max(0, getattr(self, name) - dt))
        if self.combo_timer <= 0:
            self.combo = 0
        direction = pygame.Vector2(
            int(bool(keys[pygame.K_RIGHT] or keys[pygame.K_d])) - int(bool(keys[pygame.K_LEFT] or keys[pygame.K_a] or keys[pygame.K_q])),
            int(bool(keys[pygame.K_DOWN] or keys[pygame.K_s])) - int(bool(keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_z])))
        if direction.length_squared():
            self.player += direction.normalize() * (950 if self.dash_timer > 0 else 360) * dt
        self.player.x = max(ARENA.left + 22, min(ARENA.right - 22, self.player.x))
        self.player.y = max(ARENA.top + 80, min(ARENA.bottom - 22, self.player.y))
        self.shot_timer = max(0, self.shot_timer - dt)
        if (keys[pygame.K_SPACE] or self.autofire) and self.shot_timer <= 0:
            for vx in ((-160, 0, 160) if self.spread > 0 else (0,)):
                self.bullets.append(Shot(self.player + (0, -24), pygame.Vector2(vx, -640)))
            self.shot_timer = .085 if self.rapid > 0 else .18
        if self.spawn_remaining > 0:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawn()
                self.spawn_remaining -= 1
                self.spawn_timer = max(.32, 1.1 - self.wave * .04) / self.factor
        elif not self.enemies:
            self.check_objective('clear')
            self.wave_timer += dt
            if self.wave_timer >= 2.5:
                self.next_wave()
        for shot in self.bullets + self.hostile_shots:
            shot.pos += shot.velocity * dt
        for enemy in self.enemies[:]:
            enemy.age += dt
            enemy.shot_timer -= dt
            if enemy.kind == 'boss':
                enemy.pos.y = min(ARENA.top + 130, enemy.pos.y + 80 * dt)
                enemy.pos.x = ARENA.centerx + math.sin(enemy.age * .65) * 260
            else:
                enemy.pos.y += (ENEMY_STATS[enemy.kind][2] + self.wave * 5) * self.factor * dt
                if enemy.kind == 'zigzag':
                    enemy.pos.x += math.cos(enemy.age * 3) * 120 * dt
                    enemy.pos.x = max(ARENA.left + 24, min(ARENA.right - 24, enemy.pos.x))
            if enemy.kind in ('gunner', 'boss') and enemy.shot_timer <= 0 and enemy.pos.y >= ARENA.top + 30:
                aim = self.player - enemy.pos
                if aim.length_squared():
                    aim = aim.normalize() * (165 + self.wave * 4) * self.factor
                    enraged = enemy.kind == 'boss' and enemy.hp < (70 + self.wave * 2) / 2
                    angles = (-54, -36, -18, 0, 18, 36, 54) if enraged else (-35, -17, 0, 17, 35) if enemy.kind == 'boss' else (0,)
                    for angle in angles:
                        self.hostile_shots.append(Shot(enemy.pos.copy(), aim.rotate(angle)))
                boss_interval = .72 if enemy.hp < (70 + self.wave * 2) / 2 else 1.1
                enemy.shot_timer = (boss_interval if enemy.kind == 'boss' else 2.2) / self.factor
            for bullet in self.bullets[:]:
                if bullet.pos.distance_squared_to(enemy.pos) < (enemy.radius + 5) ** 2:
                    self.bullets.remove(bullet)
                    enemy.hp -= 1
                    if enemy.hp <= 0:
                        self.kill(enemy)
                        break
            if enemy not in self.enemies:
                continue
            if enemy.pos.distance_squared_to(self.player) < (enemy.radius + 14) ** 2:
                self.damage()
                if enemy.kind != 'boss':
                    self.enemies.remove(enemy)
            elif enemy.pos.y > ARENA.bottom + enemy.radius:
                self.enemies.remove(enemy)
                self.base = max(0, self.base - 10)
                self.wave_breached = True
                self.combo = 0
                self.check_end()
            if self.state != 'playing':
                break
        for shot in self.hostile_shots[:]:
            if shot.pos.distance_squared_to(self.player) < 15 ** 2:
                self.hostile_shots.remove(shot)
                self.damage()
        bounds = ARENA.inflate(60, 160)
        self.bullets = [b for b in self.bullets if bounds.collidepoint(b.pos)]
        self.hostile_shots = [b for b in self.hostile_shots if bounds.collidepoint(b.pos)]
        if self.state != 'playing':
            return
        for pickup in self.pickups[:]:
            pickup.pos.y += 85 * dt
            if pickup.pos.distance_squared_to(self.player) < 34 ** 2:
                self.pickups.remove(pickup)
                self.collect(pickup)
            elif pickup.pos.y > ARENA.bottom + 20:
                self.pickups.remove(pickup)
        for particle in self.particles:
            particle[0] += particle[1] * dt
            particle[2] -= dt
        self.particles = [p for p in self.particles if p[2] > 0]
        # Bound object counts during very long sessions.
        self.hostile_shots = self.hostile_shots[-500:]
        self.bullets = self.bullets[-180:]

    def text(self, text, position, color=TEXT, title=False, small=False):
        surface = (self.title_font if title else self.small if small else self.font).render(text, True, color)
        self.screen.blit(surface, position)
        return surface.get_rect(topleft=position)

    def bar(self, rect, amount, color):
        pygame.draw.rect(self.screen, (35, 50, 64), rect, border_radius=3)
        fill = rect.copy()
        fill.w = max(0, round(rect.w * max(0, min(1, amount))))
        pygame.draw.rect(self.screen, color, fill, border_radius=3)

    def draw(self):
        self.screen.fill((8, 13, 23))
        self.text('NERV / COMBAT', (36, 26), CYAN, title=True)
        self.text(f'SCORE {self.score:07d}', (430, 30))
        self.text(f'WAVE {self.wave:02d} / {self.difficulty.upper()}', (704, 32), GOLD)
        self.text(f'RECORD {max(self.best, self.score):07d}', (976, 32), MUTED)
        pygame.draw.line(self.screen, (39, 57, 74), (36, 86), (1244, 86))
        pygame.draw.rect(self.screen, (11, 20, 33), ARENA, border_radius=10)
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(ARENA)
        for y in range(ARENA.top, ARENA.bottom, 48):
            pygame.draw.line(self.screen, (17, 32, 46), (ARENA.left, y), (ARENA.right, y))
        for x, y, speed in self.stars:
            pygame.draw.circle(self.screen, (72, 110, 134), (int(x), int(ARENA.top + (y - ARENA.top + self.elapsed * speed) % ARENA.h)), 1)
        for shot in self.bullets:
            pygame.draw.line(self.screen, CYAN, shot.pos, shot.pos + (0, 14), 3)
        for shot in self.hostile_shots:
            pygame.draw.circle(self.screen, PINK, (int(shot.pos.x), int(shot.pos.y)), 5)
            pygame.draw.circle(self.screen, (255, 220, 210), (int(shot.pos.x), int(shot.pos.y)), 2)
        for enemy in self.enemies:
            x, y = enemy.pos
            radius = enemy.radius
            color = {'scout': PINK, 'zigzag': GOLD, 'gunner': (167, 139, 255), 'boss': (242, 91, 114)}[enemy.kind]
            points = [(x, y + radius), (x - radius, y), (x, y - radius), (x + radius, y)]
            pygame.draw.polygon(self.screen, (37, 30, 55), points)
            pygame.draw.polygon(self.screen, color, points, 3)
            pygame.draw.circle(self.screen, color, (int(x), int(y)), max(4, radius // 4))
            if enemy.kind == 'zigzag':
                pygame.draw.lines(self.screen, color, False, [(x - 34, y - 8), (x - 24, y + 8), (x - 34, y + 16)], 2)
                pygame.draw.lines(self.screen, color, False, [(x + 34, y - 8), (x + 24, y + 8), (x + 34, y + 16)], 2)
            if enemy.kind == 'gunner':
                pygame.draw.line(self.screen, color, (x - 32, y + 12), (x + 32, y + 12), 3)
            if enemy.kind == 'boss':
                ring = pygame.Rect(int(x - 86), int(y - 86), 172, 172)
                rotation = enemy.age * .5
                for side in range(4):
                    start = rotation + side * math.pi / 2
                    pygame.draw.arc(self.screen, color, ring, start, start + .85, 2)
                pygame.draw.circle(self.screen, (255, 218, 185), (int(x), int(y)), 7)
                self.text('ANGEL / AT FIELD', (ARENA.left + 24, ARENA.top + 16), PINK, small=True)
                self.bar(pygame.Rect(ARENA.left + 24, ARENA.top + 42, ARENA.w - 48, 6), enemy.hp / (70 + self.wave * 2), PINK)
        x, y = self.player
        if self.invulnerable <= 0 or int(self.invulnerable * 14) % 2:
            pygame.draw.polygon(self.screen, (157, 132, 241), [(x, y - 25), (x - 22, y + 20), (x, y + 10), (x + 22, y + 20)])
            pygame.draw.line(self.screen, CYAN, (x, y - 12), (x, y + 8), 4)
            flame = 12 + int(6 * math.sin(self.elapsed * 35))
            pygame.draw.polygon(self.screen, GOLD, [(x - 5, y + 15), (x + 5, y + 15), (x, y + 15 + flame)])
        if self.shield or self.dash_timer > 0:
            pygame.draw.circle(self.screen, CYAN, (int(x), int(y)), 35, 2)
        for pickup in self.pickups:
            label, color = PICKUPS[pickup.kind]
            rect = pygame.Rect(pickup.pos.x - 14, pickup.pos.y - 14, 28, 28)
            pygame.draw.rect(self.screen, (20, 34, 45), rect, border_radius=6)
            pygame.draw.rect(self.screen, color, rect, 2, border_radius=6)
            self.text(label, (rect.x + 6, rect.y + 5), color, small=True)
        for position, _, life, color in self.particles:
            pygame.draw.circle(self.screen, color, (int(position.x), int(position.y)), max(1, int(life * 7)))
        if self.pulse > 0 and self.effects:
            pygame.draw.circle(self.screen, CYAN, (int(x), int(y)), int((.6 - self.pulse) * 2000), 4)
        self.screen.set_clip(previous_clip)
        pygame.draw.rect(self.screen, (39, 57, 74), ARENA, 1, border_radius=10)
        # The original illustration remains visible throughout combat.
        self.screen.blit(self.art, (976, 108))
        self.text('PILOT / UNIT 01', (976, 351), CYAN, small=True)
        self.text(f'Lives  {self.lives} / 5    Shields  {self.shield}', (952, 382))
        self.text(f'Base  {self.base} %', (952, 415), MUTED)
        self.bar(pygame.Rect(952, 441, 292, 8), self.base / 100, CYAN if self.base > 30 else PINK)
        self.text(f'AT FIELD  {int(self.energy)} %', (952, 472), GOLD)
        self.bar(pygame.Rect(952, 498, 292, 8), self.energy / 100, GOLD)
        self.text('C : projectile-clearing pulse', (952, 516), MUTED, small=True)
        self.text('SHIFT : dash' + (' ready' if self.dash_cooldown <= 0 else f' {self.dash_cooldown:.1f}s'), (952, 548), CYAN, small=True)
        self.text('F : auto-fire ' + ('ON' if self.autofire else 'OFF'), (952, 577), MUTED, small=True)
        self.text(f'Combo x{min(5, 1 + self.combo // 5)} / {self.kills} kills', (952, 606), GOLD)
        power = f'Triple {self.spread:.0f}s / Rapid {self.rapid:.0f}s'
        self.text(power, (952, 635), MUTED, small=True)
        status = 'OBJECTIVE COMPLETE' if self.objective_done else f'OBJECTIVE {self.objective_progress}/{self.objective_target}'
        self.text(status, (952, 668), CYAN if self.objective_done else GOLD, small=True)
        description = {'hunt': 'Eliminate 5 targets', 'supply': 'Collect a power-up',
                       'defend': 'Clear wave: no base breaches', 'angel': 'Defeat the Angel'}[self.objective_kind]
        self.text(description, (952, 692), MUTED, small=True)
        self.text('P : pause / save    H : help', (952, 724), CYAN, small=True)
        self.text('Arrows / WASD / ZQSD : move  |  Space : fire  |  C : pulse  |  Shift : dash  |  H : help', (36, 772), MUTED, small=True)
        if self.banner_timer > 0 and not any(e.kind == 'boss' for e in self.enemies):
            self.text(self.banner, (ARENA.left + 24, ARENA.top + 24), CYAN)
        if self.state != 'playing':
            self.draw_overlay()

    def draw_overlay(self):
        overlay = pygame.Surface(SIZE, pygame.SRCALPHA)
        overlay.fill((2, 6, 14, 215))
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Rect(244, 176, 456, 470)
        pygame.draw.rect(self.screen, (17, 27, 41), panel, border_radius=16)
        pygame.draw.rect(self.screen, (39, 57, 74), panel, 1, border_radius=16)
        self.text('PAUSE' if self.state == 'paused' else 'MISSION OVER', (284, 216), CYAN, title=True)
        self.text(f'Score {self.score}  /  Wave {self.wave}', (284, 264), MUTED)
        labels = ('Resume', 'Settings', 'Save and menu', 'Back to menu') if self.state == 'paused' else ('Play again', 'Back to menu')
        for index, label in enumerate(labels):
            rect = self.pause_rects[index]
            active = index == self.selected
            pygame.draw.rect(self.screen, (22, 54, 58) if active else (15, 24, 37), rect, border_radius=9)
            pygame.draw.rect(self.screen, CYAN if active else (39, 57, 74), rect, 1, border_radius=9)
            self.text(label, (rect.x + 18, rect.y + 16), CYAN if active else TEXT)
        if self.state == 'gameover':
            self.text(f'Targets {self.kills} / Power-ups {self.bonuses}', (284, 452), MUTED)
            self.text(f'Angels {self.bosses_defeated} / Objectives {self.objectives_completed}', (284, 484), MUTED)
            minutes, seconds = divmod(int(self.elapsed), 60)
            self.text(f'Time {minutes:02d}:{seconds:02d} / Base {self.base}%', (284, 516), MUTED)
            self.text(f'Personal best {max(self.best, self.score)}', (284, 548), GOLD)
        self.text('Arrows / Enter or mouse', (284, 604), MUTED, small=True)

    def snapshot(self):
        names = ('difficulty', 'score', 'lives', 'base', 'elapsed', 'wave', 'spawn_remaining',
                 'spawn_timer', 'wave_timer', 'shot_timer', 'invulnerable', 'dash_timer',
                 'dash_cooldown', 'shield', 'rapid', 'spread', 'energy', 'combo',
                 'combo_timer', 'kills', 'bosses_defeated', 'bonuses', 'autofire',
                 'objectives_completed', 'objective_progress', 'objective_done', 'wave_breached')
        data = {name: getattr(self, name) for name in names}
        data.update(version=1, player=list(self.player),
                    enemies=[{'pos': list(e.pos), 'kind': e.kind, 'hp': e.hp, 'age': e.age,
                              'shot_timer': e.shot_timer} for e in self.enemies],
                    bullets=[{'pos': list(s.pos), 'velocity': list(s.velocity)} for s in self.bullets],
                    hostile_shots=[{'pos': list(s.pos), 'velocity': list(s.velocity)} for s in self.hostile_shots],
                    pickups=[{'pos': list(p.pos), 'kind': p.kind} for p in self.pickups])
        return data

    def restore(self, data):
        """Validate all persisted values before applying them to a live scene."""
        def number(value, low, high, integer=False):
            valid = type(value) is int if integer else type(value) in (int, float)
            if not valid or not math.isfinite(value) or not low <= value <= high:
                raise ValueError('invalid save number')
            return value

        def vector(value, speed=False):
            if not isinstance(value, list) or len(value) != 2:
                raise ValueError('invalid vector')
            bound = 2000 if speed else 5000
            return pygame.Vector2(*(number(v, -bound, bound) for v in value))

        def sequence(key, limit):
            result = data.get(key)
            if not isinstance(result, list) or len(result) > limit or any(not isinstance(v, dict) for v in result):
                raise ValueError('invalid save collection')
            return result

        try:
            if data.get('version') != 1 or data.get('difficulty') not in DIFFICULTIES:
                raise ValueError('unsupported save')
            values = {}
            ranges = {'score': (0, 1_000_000_000), 'lives': (1, 5), 'base': (1, 100), 'wave': (1, 100000),
                      'spawn_remaining': (0, 30), 'shield': (0, 2), 'combo': (0, 1000000),
                      'kills': (0, 1000000), 'bosses_defeated': (0, 100000), 'bonuses': (0, 1000000)}
            for key, (low, high) in ranges.items():
                values[key] = number(data[key], low, high, integer=True)
            for key in ('elapsed', 'spawn_timer', 'wave_timer', 'shot_timer', 'invulnerable',
                        'dash_timer', 'dash_cooldown', 'rapid', 'spread', 'energy', 'combo_timer'):
                values[key] = number(data[key], -1 if key == 'shot_timer' else 0, 10_000_000 if key == 'elapsed' else 100)
            # Optional fields keep saves from the previous release compatible.
            for key in ('objectives_completed', 'objective_progress'):
                values[key] = number(data.get(key, 0), 0, 1000000, integer=True)
            for key in ('objective_done', 'wave_breached'):
                value = data.get(key, False)
                if type(value) is not bool:
                    raise ValueError('invalid objective state')
                values[key] = value
            if type(data['autofire']) is not bool:
                raise ValueError('invalid autofire')
            player = vector(data['player'])
            if not ARENA.collidepoint(player):
                raise ValueError('player outside arena')
            enemies = []
            for item in sequence('enemies', 100):
                if item['kind'] not in ENEMY_STATS:
                    raise ValueError('invalid enemy kind')
                enemies.append(Enemy(vector(item['pos']), item['kind'], number(item['hp'], 1, 1_000_000, True),
                                     number(item['age'], 0, 10_000_000), number(item['shot_timer'], -100, 100)))
            shots = {}
            for key, limit in (('bullets', 180), ('hostile_shots', 500)):
                shots[key] = [Shot(vector(item['pos']), vector(item['velocity'], True)) for item in sequence(key, limit)]
            pickups = []
            for item in sequence('pickups', 100):
                if item['kind'] not in PICKUPS:
                    raise ValueError('invalid pickup')
                pickups.append(Pickup(vector(item['pos']), item['kind']))
        except (KeyError, TypeError, AttributeError, OverflowError) as error:
            raise ValueError('invalid save') from error
        self.reset()
        for key, value in values.items():
            setattr(self, key, value)
        self.difficulty = data['difficulty']
        self.factor = DIFFICULTIES[self.difficulty]
        self.autofire = data['autofire']
        self.player = player
        self.enemies = enemies
        self.bullets = shots['bullets']
        self.hostile_shots = shots['hostile_shots']
        self.pickups = pickups
        self.state = 'paused'
        self.message('SAVE RESTORED / RESUME WHEN READY')


if __name__ == '__main__':
    from main import main
    main()
