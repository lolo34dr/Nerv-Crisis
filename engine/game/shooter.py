"""A small, time-based arcade shooter with an explicit menu/pause/game-over loop."""
import math
import random

import pygame

from .variable import (WIDTH, HEIGHT, BLACK, TEXT_COLOR, HIGHLIGHT_COLOR,
                       ASSETS, pixel_font, opening_music)


class Game:
    def __init__(self, seed=None):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Nerv : Crisis')
        pygame.display.set_icon(pygame.image.load(str(ASSETS / 'images/icon.png')))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(pixel_font, 20)
        self.title_font = pygame.font.Font(pixel_font, 52)
        self.rng = random.Random(seed)
        self.stars = [(self.rng.randrange(WIDTH), self.rng.randrange(HEIGHT),
                       self.rng.uniform(15, 70)) for _ in range(90)]
        self.running = True
        self.muted = False
        self.best = 0
        self.state = 'menu'
        self.music_available = False
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.load(opening_music)
                pygame.mixer.music.set_volume(.25)
                pygame.mixer.music.play(-1)
                self.music_available = True
            except pygame.error:
                pass
        self.reset()

    def reset(self):
        self.player = pygame.Vector2(WIDTH / 2, HEIGHT - 65)
        self.bullets = []
        self.enemies = []
        self.particles = []
        self.score = 0
        self.lives = 3
        self.elapsed = 0.0
        self.spawn_timer = .5
        self.shot_timer = 0.0
        self.invulnerable = 0.0

    @property
    def level(self):
        return 1 + int(self.elapsed / 20)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.state == 'playing':
                    self.state = 'paused'
                elif self.state == 'paused':
                    self.state = 'playing'
                else:
                    self.running = False
            elif event.key == pygame.K_RETURN and self.state in ('menu', 'gameover'):
                self.reset()
                self.state = 'playing'
            elif event.key == pygame.K_p and self.state in ('playing', 'paused'):
                self.state = 'paused' if self.state == 'playing' else 'playing'
            elif event.key == pygame.K_m:
                self.muted = not self.muted
                if self.music_available:
                    pygame.mixer.music.set_volume(0 if self.muted else .25)
        elif event.type == pygame.WINDOWFOCUSLOST and self.state == 'playing':
            self.state = 'paused'

    def burst(self, position, color):
        for _ in range(16):
            angle = self.rng.uniform(0, math.tau)
            velocity = pygame.Vector2(math.cos(angle), math.sin(angle)) * self.rng.uniform(45, 190)
            self.particles.append([pygame.Vector2(position), velocity, .5, color])

    def damage(self):
        if self.invulnerable > 0:
            return
        self.lives -= 1
        self.invulnerable = 1.5
        self.burst(self.player, (255, 90, 90))
        if self.lives <= 0:
            self.state = 'gameover'
            self.best = max(self.best, self.score)

    def update(self, dt, keys=None):
        if self.state != 'playing':
            return
        keys = pygame.key.get_pressed() if keys is None else keys
        self.elapsed += dt
        self.invulnerable = max(0, self.invulnerable - dt)
        direction = pygame.Vector2(
            int(bool(keys[pygame.K_RIGHT] or keys[pygame.K_d])) - int(bool(keys[pygame.K_LEFT] or keys[pygame.K_a] or keys[pygame.K_q])),
            int(bool(keys[pygame.K_DOWN] or keys[pygame.K_s])) - int(bool(keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_z])))
        if direction.length_squared():
            self.player += direction.normalize() * 360 * dt
        self.player.x = max(20, min(WIDTH - 20, self.player.x))
        self.player.y = max(70, min(HEIGHT - 20, self.player.y))
        self.shot_timer -= dt
        if keys[pygame.K_SPACE] and self.shot_timer <= 0:
            self.bullets.append(pygame.Vector2(self.player.x, self.player.y - 24))
            self.shot_timer = .16
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.enemies.append(pygame.Vector2(self.rng.randrange(25, WIDTH - 25), -25))
            self.spawn_timer = max(.22, .85 - self.level * .07)
        for bullet in self.bullets:
            bullet.y -= 620 * dt
        for enemy in self.enemies[:]:
            enemy.y += (90 + self.level * 22) * dt
            hit = next((b for b in self.bullets if b.distance_squared_to(enemy) < 26 ** 2), None)
            if hit is not None:
                self.bullets.remove(hit)
                self.enemies.remove(enemy)
                self.score += 100
                self.burst(enemy, HIGHLIGHT_COLOR)
            elif enemy.distance_squared_to(self.player) < 33 ** 2 or enemy.y > HEIGHT + 25:
                self.enemies.remove(enemy)
                self.damage()
                if self.state == 'gameover':
                    break
        self.bullets = [b for b in self.bullets if b.y > -20]
        for particle in self.particles:
            particle[0] += particle[1] * dt
            particle[2] -= dt
        self.particles = [p for p in self.particles if p[2] > 0]

    def text(self, text, y, color=TEXT_COLOR, large=False):
        surface = (self.title_font if large else self.font).render(text, True, color)
        self.screen.blit(surface, surface.get_rect(center=(WIDTH // 2, y)))

    def draw(self):
        self.screen.fill(BLACK)
        for x, y, speed in self.stars:
            pygame.draw.circle(self.screen, (70, 85, 110), (int(x), int((y + self.elapsed * speed) % HEIGHT)), 1)
        for bullet in self.bullets:
            pygame.draw.line(self.screen, (100, 255, 205), bullet, bullet + (0, 12), 4)
        for enemy in self.enemies:
            x, y = enemy
            pygame.draw.polygon(self.screen, (235, 65, 100), [(x, y + 22), (x - 22, y), (x, y - 22), (x + 22, y)])
            pygame.draw.circle(self.screen, HIGHLIGHT_COLOR, (int(x), int(y)), 6)
        if self.state != 'menu' and (self.invulnerable <= 0 or int(self.invulnerable * 12) % 2):
            x, y = self.player
            pygame.draw.polygon(self.screen, (120, 100, 240), [(x, y - 24), (x - 20, y + 18), (x, y + 8), (x + 20, y + 18)])
            pygame.draw.line(self.screen, (110, 255, 185), (x, y - 12), (x, y + 6), 4)
        for position, _, life, color in self.particles:
            pygame.draw.circle(self.screen, color, (int(position.x), int(position.y)), max(1, int(life * 7)))
        hud = self.font.render(f'SCORE {self.score:06d}    VIES {self.lives}    VAGUE {self.level}', True, TEXT_COLOR)
        self.screen.blit(hud, (20, 18))
        if self.state != 'playing':
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((5, 8, 20, 205))
            self.screen.blit(overlay, (0, 0))
            title = {'menu': 'NERV : CRISIS', 'paused': 'PAUSE', 'gameover': 'MISSION TERMINEE'}[self.state]
            self.text(title, 200, HIGHLIGHT_COLOR, True)
            if self.state == 'gameover':
                self.text(f'Score : {self.score}    Record session : {self.best}', 280)
            self.text('P / ECHAP : reprendre' if self.state == 'paused' else 'ENTREE : jouer', 340)
            self.text('Fleches / ZQSD / WASD : deplacement', 410)
            self.text('ESPACE : tirer    P : pause    M : musique', 445)
            self.text('Protegez la base. Chaque impact coute une vie.', 505)
        pygame.display.flip()

    def run(self):
        try:
            while self.running:
                dt = min(self.clock.tick(60) / 1000, .05)
                for event in pygame.event.get():
                    self.handle_event(event)
                self.update(dt)
                self.draw()
        finally:
            pygame.quit()
