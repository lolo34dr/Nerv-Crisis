"""NERV terminal: original artwork and soundtrack, with a scalable interface."""
import argparse
import math
from pathlib import Path

import pygame

from engine.game import variable
from engine.game.shooter import Game
from engine.game.assets import ResourceLoader, CombatAssets
from engine.game.storage import Profile, DIFFICULTIES, ACHIEVEMENTS

ROOT = Path(__file__).resolve().parent
SIZE = (1280, 800)
BG = (8, 13, 23)
PANEL = (15, 24, 37)
BORDER = (39, 57, 74)
TEXT = (229, 238, 243)
MUTED = (143, 165, 182)
CYAN = (92, 232, 210)
PINK = (241, 112, 172)


class Menu:
    def __init__(self, skip_intro=False, data_directory=None, fullscreen=True):
        pygame.display.init()
        pygame.font.init()
        desktop = pygame.display.get_desktop_sizes()[0]
        self.window_size = (min(SIZE[0], desktop[0]), min(SIZE[1], desktop[1]))
        self.fullscreen = fullscreen
        self.window = pygame.display.set_mode((0, 0) if fullscreen else self.window_size,
                                              pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE)
        pygame.display.set_caption('NERV Crisis / Pilot terminal')
        self.canvas = pygame.Surface(SIZE)
        self.logo = pygame.image.load(str(variable.ASSETS / 'images/icon.png')).convert_alpha()
        pygame.display.set_icon(self.logo)
        self.splash_logo = pygame.transform.smoothscale(self.logo, (440, 440))
        self.bootstrap_font = pygame.font.Font(None, 28)
        self.logo_small = None
        self.art = None
        self.combat_assets = None
        self.fonts = {}
        self.body_fonts = {}
        self.clock = pygame.time.Clock()
        self.running = True
        self.selected = 0
        self.modal = None
        self.modal_selected = 0
        self.data_directory = data_directory
        self.profile = None
        self.music_paused = False
        self.volume = .6
        self.effects = True
        self.difficulty = 'normal'
        self.settings_dirty = False
        self.dragging_volume = False
        self.game = None
        self.notice = ''
        self.notice_until = 0
        self.intro = not skip_intro
        self.intro_elapsed = 0.0
        self.time = 0.0
        self.menu_rects = [pygame.Rect(64, 302 + i * 94, 588, 80) for i in range(4)]
        self.music_rect = pygame.Rect(736, 638, 480, 96)
        self.slider = pygame.Rect(308, 354, 664, 24)
        self.close_rect = pygame.Rect(920, 194, 52, 44)
        self.modal_buttons = [pygame.Rect(308, 490, 316, 64), pygame.Rect(656, 490, 316, 64)]
        self.audio_available = False
        self.hover_sound = None
        self.click_sound = None
        self.background = None
        self.loader = ResourceLoader([
            ('Read pilot profile', self.load_profile),
            ('Load interface fonts', self.load_fonts),
            ('Decode original artwork', self.load_art),
            ('Prepare combat graphics', self.load_combat_assets),
            ('Initialize soundtrack', self.load_music),
            ('Decode sound effects', self.load_sounds),
            ('Build terminal background', self.load_background),
        ])
        if skip_intro:
            # Even when the splash is skipped, show real loading progress.
            while self.running and not self.loader.ready and not self.loader.error:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                self.draw_loading()
                self.present()
                self.loader.step()
            self.draw_loading()
            self.present()

    def load_profile(self):
        self.profile = Profile(self.data_directory)
        self.music_paused = self.profile.settings['music_paused']
        self.volume = self.profile.settings['volume']
        self.effects = self.profile.settings['effects']
        self.difficulty = self.profile.settings['difficulty']
        if self.profile.error:
            self.notify(self.profile.error)

    def load_fonts(self):
        self.fonts = {size: pygame.font.Font(variable.pixel_font, size) for size in (16, 20, 28, 32, 52, 62)}
        self.body_fonts = {size: pygame.font.Font(None, size) for size in (20, 24, 28, 32)}

    def load_art(self):
        self.source_art = pygame.image.load(str(variable.ASSETS / 'images/evangelion.png')).convert_alpha()
        self.art = pygame.transform.smoothscale(self.source_art, (384, 384))
        self.logo_small = pygame.transform.smoothscale(self.logo, (44, 44))

    def load_combat_assets(self):
        self.combat_assets = CombatAssets.load(self.source_art, self.fonts[32])

    def load_music(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(variable.opening_music)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(-1)
            self.audio_available = True
            self.sync_music()
        except (pygame.error, OSError):
            # Audio is optional; the other resources and gameplay still load.
            self.audio_available = False

    def load_sounds(self):
        if self.audio_available:
            try:
                self.hover_sound = pygame.mixer.Sound(variable.over_soundeffect)
                self.click_sound = pygame.mixer.Sound(variable.start_soundeffect)
                self.hover_sound.set_volume(.25)
                self.click_sound.set_volume(.35)
            except (pygame.error, OSError):
                self.hover_sound = self.click_sound = None

    def load_background(self):
        self.background = self.make_background()

    def make_background(self):
        surface = pygame.Surface(SIZE)
        for y in range(SIZE[1]):
            t = y / SIZE[1]
            pygame.draw.line(surface, (8 + int(4 * t), 13 + int(6 * t), 23 + int(9 * t)), (0, y), (SIZE[0], y))
        for x in range(0, SIZE[0], 48):
            pygame.draw.line(surface, (17, 27, 38), (x, 0), (x, SIZE[1]))
        for y in range(0, SIZE[1], 48):
            pygame.draw.line(surface, (17, 27, 38), (0, y), (SIZE[0], y))
        return surface

    def viewport(self):
        width, height = self.window.get_size()
        scale = min(width / SIZE[0], height / SIZE[1])
        rect = pygame.Rect(0, 0, max(1, round(SIZE[0] * scale)), max(1, round(SIZE[1] * scale)))
        rect.center = (width // 2, height // 2)
        return rect

    def logical_position(self, position):
        rect = self.viewport()
        if not rect.collidepoint(position):
            return None
        return ((position[0] - rect.x) * SIZE[0] / rect.w,
                (position[1] - rect.y) * SIZE[1] / rect.h)

    def present(self):
        rect = self.viewport()
        self.window.fill((0, 0, 0) if self.intro else (3, 6, 12))
        pygame.transform.smoothscale(self.canvas, rect.size, self.window.subsurface(rect))
        pygame.display.flip()

    def text(self, value, pos, size=24, color=TEXT, pixel=False):
        font = (self.fonts if pixel else self.body_fonts)[size]
        surface = font.render(value, True, color)
        self.canvas.blit(surface, pos)
        return surface.get_rect(topleft=pos)

    def paragraph(self, value, rect, size=28, color=MUTED):
        """Wrap body copy to a fixed card width; never paint outside its bounds."""
        font = self.body_fonts[size]
        old_clip = self.canvas.get_clip()
        self.canvas.set_clip(rect)
        y = rect.y
        for part in value.split('\n'):
            line = ''
            for word in part.split():
                candidate = (line + ' ' + word).strip()
                if font.size(candidate)[0] > rect.w and line:
                    self.text(line, (rect.x, y), size, color)
                    y += font.get_linesize() + 5
                    line = word
                else:
                    line = candidate
            self.text(line, (rect.x, y), size, color)
            y += font.get_linesize() + 5
        self.canvas.set_clip(old_clip)
        return y

    def card(self, rect, color=PANEL, border=BORDER, radius=14):
        pygame.draw.rect(self.canvas, color, rect, border_radius=radius)
        pygame.draw.rect(self.canvas, border, rect, 1, border_radius=radius)

    def sound(self, sound):
        if sound:
            sound.play()

    def toggle_music(self):
        self.music_paused = not self.music_paused
        self.settings_dirty = True
        self.sync_music()

    def sync_music(self):
        if self.audio_available:
            if self.music_paused:
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.unpause()

    def set_volume(self, volume):
        self.volume = max(0, min(1, round(volume, 2)))
        self.settings_dirty = True
        if self.audio_available:
            pygame.mixer.music.set_volume(self.volume)

    def open_modal(self, kind):
        self.modal = kind
        self.modal_selected = 1 if kind == 'quit' else 0
        self.dragging_volume = False

    def active_modal_buttons(self):
        return [pygame.Rect(308, 490, 664, 64)] if self.modal == 'help' else self.modal_buttons

    def activate(self, index):
        self.sound(self.click_sound)
        self.open_modal(('selector', 'load', 'lab', 'quit')[index])

    def persist_settings(self):
        if not self.settings_dirty:
            return
        self.profile.settings.update(volume=self.volume, music_paused=self.music_paused,
                                     effects=self.effects, difficulty=self.difficulty)
        if not self.profile.write():
            self.notify(self.profile.error)
        else:
            self.settings_dirty = False

    def notify(self, text):
        self.notice = text
        self.notice_until = pygame.time.get_ticks() + 5000

    def launch_game(self, resume=False):
        if not self.loader.ready:
            return
        game = Game(self.canvas, difficulty=self.difficulty,
                    best=self.profile.highscores[self.difficulty], effects=self.effects,
                    assets=self.combat_assets)
        if resume:
            try:
                game.restore(self.profile.saved_game)
                game.best = self.profile.highscores[game.difficulty]
            except ValueError:
                self.notify('Save is incompatible or damaged. Start a new game.')
                self.modal = None
                return
        self.game = game
        self.modal = None
        self.persist_settings()

    def record_game(self):
        if self.game is not None and not self.game.reported:
            self.profile.settings.update(volume=self.volume, music_paused=self.music_paused,
                                         effects=self.effects, difficulty=self.difficulty)
            success = self.profile.record(self.game)
            if not success:
                self.notify(self.profile.error)
            self.game.reported = True
            return success
        return not bool(self.profile.error)

    def game_action(self, action):
        if action == 'settings':
            self.open_modal('lab')
        elif action == 'save':
            previous = self.profile.saved_game
            self.profile.saved_game = self.game.snapshot()
            self.game.reported = False
            if self.profile.record(self.game):
                self.game = None
                self.notify('Mission saved. Select Load to continue.')
            else:
                self.profile.saved_game = previous
                self.notify(self.profile.error)
        elif action == 'menu':
            saved = self.record_game()
            self.game = None
            self.notify('Back at the terminal. Records and achievements saved.' if saved else self.profile.error)

    def cycle_difficulty(self, step):
        names = list(DIFFICULTIES)
        self.difficulty = names[(names.index(self.difficulty) + step) % len(names)]
        self.settings_dirty = True

    def toggle_effects(self):
        self.effects = not self.effects
        self.settings_dirty = True
        if self.game:
            self.game.effects = self.effects
            if not self.effects:
                self.game.particles.clear()

    def saved_summary(self):
        data = self.profile.saved_game or {}
        wave = data.get('wave')
        score = data.get('score')
        wave = wave if type(wave) is int and 1 <= wave <= 100000 else '?'
        score = score if type(score) is int and 0 <= score <= 1_000_000_000 else '?'
        return f'Wave {wave} / Score {score}'

    def modal_action(self, index):
        if self.modal == 'quit':
            if index == 0:
                self.running = False
            else:
                self.modal = None
        elif self.modal == 'selector' and index == 0:
            self.launch_game()
        elif self.modal == 'load' and index == 0:
            if self.profile.saved_game:
                self.launch_game(resume=True)
            else:
                self.open_modal('selector')
        elif self.modal == 'records' and index == 0:
            self.open_modal('selector')
        elif self.modal == 'lab' and index == 0:
            self.toggle_music()
        else:
            self.modal = None
            self.persist_settings()

    def handle_event(self, event):
        if self.game and event.type == pygame.WINDOWFOCUSLOST:
            self.game.handle_event(event)
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            self.dragging_volume = False
        if not self.intro and not self.loader.ready:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    self.loader.retry()
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                self.fullscreen = not self.fullscreen
                if self.fullscreen:
                    self.window_size = self.window.get_size()
                self.window = pygame.display.set_mode((0, 0) if self.fullscreen else self.window_size,
                    pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE)
                return
            if self.intro:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    self.intro = False
                return
            if event.key == pygame.K_h:
                if self.game and self.game.state == 'playing':
                    self.game.state = 'paused'
                if self.modal == 'help':
                    self.modal = None
                else:
                    self.open_modal('help')
                return
            if event.key == pygame.K_m:
                self.toggle_music()
                return
            if self.game and not self.modal:
                # Record a finished run before the replay event resets its counters.
                if self.game.state == 'gameover':
                    self.record_game()
                self.game_action(self.game.handle_event(event))
                return
            if self.modal:
                if event.key == pygame.K_ESCAPE:
                    self.modal = None
                    self.dragging_volume = False
                    self.persist_settings()
                elif self.modal == 'lab' and event.key == pygame.K_v:
                    self.toggle_effects()
                elif self.modal == 'selector' and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    self.cycle_difficulty(1 if event.key == pygame.K_RIGHT else -1)
                elif self.modal == 'lab' and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    self.set_volume(self.volume + (.1 if event.key == pygame.K_RIGHT else -.1))
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
                    self.modal_selected = (self.modal_selected + 1) % len(self.active_modal_buttons())
                elif event.key == pygame.K_RETURN:
                    self.modal_action(self.modal_selected)
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
                self.selected = (self.selected + (-1 if event.key == pygame.K_UP else 1)) % 4
                self.sound(self.hover_sound)
            elif event.key == pygame.K_b:
                self.open_modal('records')
            elif event.key == pygame.K_RETURN:
                self.activate(self.selected)
            elif event.key == pygame.K_ESCAPE:
                self.open_modal('quit')
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_volume = False
            self.persist_settings()
        if event.type not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            return
        pos = self.logical_position(event.pos)
        if pos is None:
            return
        click = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
        if self.game and not self.modal:
            if self.game.state == 'gameover':
                self.record_game()
            self.game_action(self.game.handle_event(event, pos))
            return
        if self.intro:
            if click:
                self.intro = False
            return
        if self.modal:
            slider_clicked = click and self.slider.inflate(24, 24).collidepoint(pos)
            if self.modal == 'lab' and (slider_clicked or self.dragging_volume):
                self.dragging_volume = True
                self.set_volume((pos[0] - self.slider.x) / self.slider.w)
            elif click and self.close_rect.collidepoint(pos):
                self.modal = None
                self.persist_settings()
            elif click and self.modal == 'lab' and pygame.Rect(308, 420, 664, 46).collidepoint(pos):
                self.toggle_effects()
            elif click and self.modal == 'selector' and 414 <= pos[1] <= 460:
                for index, name in enumerate(DIFFICULTIES):
                    if pygame.Rect(308 + index * 226, 414, 212, 46).collidepoint(pos):
                        self.difficulty = name
                        self.settings_dirty = True
            else:
                for index, rect in enumerate(self.active_modal_buttons()):
                    if rect.collidepoint(pos):
                        self.modal_selected = index
                        if click:
                            self.modal_action(index)
                        break
            return
        for index, rect in enumerate(self.menu_rects):
            if rect.collidepoint(pos):
                if self.selected != index:
                    self.sound(self.hover_sound)
                self.selected = index
                if click:
                    self.activate(index)
                return
        if click and pygame.Rect(64, 688, 588, 50).collidepoint(pos):
            self.open_modal('records')
        if click and self.music_rect.collidepoint(pos):
            self.toggle_music()

    def update(self, dt):
        self.time += dt
        if self.intro:
            self.intro_elapsed += dt
            if self.intro_elapsed >= 2:
                self.intro = False
            return
        if not self.loader.ready:
            self.loader.step()
            return
        if self.game and not self.modal:
            self.game.update(dt)
            if self.game.state == 'gameover':
                self.record_game()

    def draw_header(self):
        self.canvas.blit(self.logo_small, (64, 30))
        self.text('NERV', (124, 33), 28, pixel=True)
        self.text('PILOT TERMINAL / TOKYO-3', (126, 65), 20, MUTED)
        self.card(pygame.Rect(1010, 38, 206, 36), border=(45, 92, 83), radius=18)
        pygame.draw.circle(self.canvas, CYAN, (1030, 56), 4)
        self.text('MAGI SYSTEM ONLINE', (1044, 47), 20, CYAN)
        pygame.draw.line(self.canvas, BORDER, (64, 102), (1216, 102))

    def draw(self):
        if self.intro:
            self.draw_intro()
            return
        if not self.loader.ready:
            self.draw_loading()
            return
        if self.game:
            self.game.draw()
            if self.modal:
                self.draw_modal()
            if self.notice and pygame.time.get_ticks() < self.notice_until:
                self.card(pygame.Rect(224, 690, 832, 52), border=PINK)
                self.paragraph(self.notice, pygame.Rect(244, 704, 792, 32), 24, TEXT)
            return
        self.canvas.blit(self.background, (0, 0))
        self.draw_header()
        self.text('OPERATIONS / 01', (64, 140), 20, CYAN)
        self.text('NERV', (60, 171), 62, pixel=True)
        self.text('CRISIS', (262, 171), 62, CYAN, pixel=True)
        self.text('Take control. Defend the base.', (66, 252), 28, MUTED)
        names = ('New Game', 'Load', 'Lab', 'Quit')
        descriptions = ('Deploy on a new mission', 'Continue your saved mission',
                        'Audio, effects and controls', 'Close the terminal')
        for index, rect in enumerate(self.menu_rects):
            active = index == self.selected
            self.card(rect, (20, 43, 52) if active else PANEL, CYAN if active else BORDER)
            if active:
                pygame.draw.rect(self.canvas, CYAN, (rect.x, rect.y + 20, 3, 40), border_radius=2)
            self.text(f'0{index + 1}', (rect.x + 22, rect.y + 27), 20, CYAN if active else MUTED, pixel=True)
            self.text(names[index], (rect.x + 80, rect.y + 12), 28, TEXT, pixel=True)
            self.text(descriptions[index], (rect.x + 80, rect.y + 49), 24, MUTED)
            self.text('>', (rect.right - 36, rect.y + 27), 24, CYAN if active else MUTED)
        # Artwork and audio share a column and spacing, with no text over the illustration.
        self.card(pygame.Rect(736, 140, 480, 474))
        self.text('EVA ARCHIVE', (760, 159), 16, CYAN, pixel=True)
        self.text('UNIT / 01', (1091, 161), 20, MUTED)
        self.canvas.blit(self.art, (784, 196))
        self.text('NEON GENESIS EVANGELION', (784, 586), 20, MUTED)
        self.card(self.music_rect)
        pygame.draw.circle(self.canvas, (30, 66, 68), (768, 686), 18)
        if self.music_paused:
            pygame.draw.polygon(self.canvas, CYAN, [(763, 677), (763, 695), (776, 686)])
        else:
            for x in (762, 770):
                pygame.draw.rect(self.canvas, CYAN, (x, 678, 4, 16), border_radius=1)
        self.text("The Cruel Angel's Thesis", (802, 655), 28)
        status = 'Paused' if self.music_paused else 'Playing on repeat'
        if not self.audio_available:
            status = 'Audio output unavailable'
        self.text(status + '  ·  M : pause', (802, 691), 24, MUTED)
        for index in range(12):
            height = (7 + int(10 * (1 + math.sin(self.time * 4 + index)))) if not self.music_paused and self.audio_available else 4
            pygame.draw.rect(self.canvas, CYAN, (1136 + index * 4, 709 - height, 2, height))
        self.text('ARCADE SURVIVAL / B : RECORDS & ACHIEVEMENTS', (66, 698), 20, CYAN)
        self.text(f'Record {self.profile.highscores[self.difficulty]:07d}  /  Achievements {len(self.profile.achievements)}/{len(ACHIEVEMENTS)}', (66, 722), 24, MUTED)
        pygame.draw.line(self.canvas, BORDER, (64, 754), (1216, 754))
        self.text('Arrows : select    Enter : confirm    M : music    H : help    F11 : fullscreen', (64, 770), 20, MUTED)
        self.text('© 2025 0-cyz-0', (1092, 770), 20, MUTED)
        if self.notice and pygame.time.get_ticks() < self.notice_until:
            self.card(pygame.Rect(224, 690, 832, 52), border=PINK)
            self.paragraph(self.notice, pygame.Rect(244, 704, 792, 32), 24, TEXT)
        if self.modal:
            self.draw_modal()

    def draw_intro(self):
        # Logo-only splash, matching the original black presentation.
        self.canvas.fill((0, 0, 0))
        fade_in = min(1, self.intro_elapsed / .6)
        fade_out = min(1, max(0, (2 - self.intro_elapsed) / .6))
        logo = self.splash_logo.copy()
        logo.set_alpha(round(255 * min(fade_in, fade_out)))
        self.canvas.blit(logo, logo.get_rect(center=(SIZE[0] // 2, SIZE[1] // 2 - 20)))
        caption = self.bootstrap_font.render('A CYZ GAME', True, (170, 180, 190))
        caption.set_alpha(logo.get_alpha())
        self.canvas.blit(caption, caption.get_rect(center=(SIZE[0] // 2, 680)))

    def draw_loading(self):
        self.canvas.fill((0, 0, 0))
        title = self.bootstrap_font.render('NERV / LOADING RESOURCES', True, CYAN)
        self.canvas.blit(title, (320, 292))
        rect = pygame.Rect(320, 370, 640, 6)
        pygame.draw.rect(self.canvas, BORDER, rect, border_radius=3)
        fill = rect.copy()
        fill.w = round(rect.w * self.loader.progress)
        pygame.draw.rect(self.canvas, PINK if self.loader.error else CYAN, fill, border_radius=3)
        count = self.bootstrap_font.render(
            f'{self.loader.completed} / {len(self.loader.jobs)} completed  ·  {round(self.loader.progress * 100)}%', True, TEXT)
        self.canvas.blit(count, (320, 328))
        label = ('Failed: ' if self.loader.error else 'Next: ') + self.loader.label
        if self.loader.ready:
            label = 'All resources ready'
        status = self.bootstrap_font.render(label, True, PINK if self.loader.error else MUTED)
        self.canvas.blit(status, (320, 410))
        hint = 'R : retry    Esc : quit' if self.loader.error else 'Artwork, fonts and audio are being prepared. Esc : quit'
        self.canvas.blit(self.bootstrap_font.render(hint, True, MUTED), (320, 472))
        if self.loader.error:
            # Keep long filesystem errors in the terminal rather than overflowing the screen.
            detail = self.loader.error[:90]
            self.canvas.blit(pygame.font.Font(None, 22).render(detail, True, MUTED), (160, 532))

    def draw_modal(self):
        shade = pygame.Surface(SIZE, pygame.SRCALPHA)
        shade.fill((2, 6, 14, 225))
        self.canvas.blit(shade, (0, 0))
        self.card(pygame.Rect(260, 170, 760, 460), (17, 27, 41), BORDER, 20)
        titles = {'selector': 'SELECT A MISSION', 'lab': 'LAB / SETTINGS',
                  'load': 'SAVED MISSION', 'records': 'RECORDS / ACHIEVEMENTS', 'help': 'PILOT FIELD GUIDE', 'quit': 'EXIT TERMINAL?'}
        self.text(titles[self.modal], (308, 211), 28, CYAN, pixel=True)
        self.card(self.close_rect, border=BORDER, radius=8)
        self.text('×', (937, 201), 32, MUTED)
        pygame.draw.line(self.canvas, BORDER, (308, 266), (972, 266))
        if self.modal == 'help':
            lines = [('Move', 'Arrows / WASD / ZQSD'), ('Fire / auto-fire', 'Space / F'),
                     ('Dash / AT Field pulse', 'Shift / C'), ('Pause / help', 'P or Esc / H'),
                     ('Power-ups', '+ heal   S shield   R rapid   T triple   E energy'),
                     ('Save progress', 'Pause > Save and menu; then Load to continue')]
            for index, (action, key) in enumerate(lines):
                y = 300 + index * 28
                self.text(action, (308, y), 24, CYAN)
                self.text(key, (532, y), 20, TEXT)
            buttons = ('Back',)
        elif self.modal == 'records':
            scores = self.profile.highscores
            self.text(f'Cadet {scores["cadet"]}  /  Normal {scores["normal"]}  /  Expert {scores["expert"]}', (308, 300), 24, CYAN)
            for index, (key, title) in enumerate(ACHIEVEMENTS.items()):
                unlocked = key in self.profile.achievements
                self.text(('[OK] ' if unlocked else '[  ] ') + title, (308, 330 + index * 24), 24, CYAN if unlocked else MUTED)
            buttons = ('New mission', 'Back')
        elif self.modal == 'lab':
            self.text('Music volume', (308, 301), 28)
            self.text(f'{round(self.volume * 100):3d} %', (902, 301), 28, CYAN)
            pygame.draw.rect(self.canvas, BORDER, (308, 364, 664, 4), border_radius=2)
            pygame.draw.rect(self.canvas, CYAN, (308, 364, round(664 * self.volume), 4), border_radius=2)
            pygame.draw.circle(self.canvas, CYAN, (308 + round(664 * self.volume), 366), 8)
            self.text('Drag the slider or use Left / Right.', (308, 400), 24, MUTED)
            self.text('V : particles / effects  ' + ('ON' if self.effects else 'OFF'), (308, 439), 24, CYAN)
            buttons = ('Music : ' + ('pause' if self.music_paused else 'playing'), 'Back')
        else:
            descriptions = {
                'selector': 'SHOOTER / Defend Tokyo-3\nBosses every 5 waves, power-ups and combos. Choose a difficulty with Left / Right.',
                'load': (self.saved_summary() + '\nContinue your saved mission. Records and achievements are kept between sessions.' if self.profile.saved_game else 'No saved mission.\nDuring a mission, open Pause then Save and menu. Your high scores are always kept.'),
                'quit': 'Would you like to close NERV Crisis?\nYou can return to the terminal by launching the game again.'}
            self.paragraph(descriptions[self.modal], pygame.Rect(308, 305, 664, 145), 28)
            if self.modal == 'selector':
                for index, name in enumerate(DIFFICULTIES):
                    rect = pygame.Rect(308 + index * 226, 414, 212, 46)
                    self.card(rect, border=CYAN if name == self.difficulty else BORDER, radius=8)
                    self.text(name.capitalize(), (rect.x + 20, rect.y + 14), 24, CYAN if name == self.difficulty else MUTED)
            buttons = {'selector': ('Launch Shooter', 'Back'), 'load': ('Continue' if self.profile.saved_game else 'New game', 'Back'),
                       'quit': ('Quit', 'Cancel')}[self.modal]
        for index, (rect, title) in enumerate(zip(self.active_modal_buttons(), buttons)):
            active = index == self.modal_selected
            self.card(rect, (22, 54, 58) if active else PANEL, CYAN if active else BORDER, 10)
            font = self.body_fonts[28]
            self.text(title, (rect.centerx - font.size(title)[0] // 2, rect.y + 21), 28, CYAN if active else TEXT)
        self.text('Enter : confirm     Esc : back', (308, 586), 24, MUTED)

    def run(self):
        try:
            while self.running:
                dt = min(self.clock.tick(60) / 1000, .1)
                for event in pygame.event.get():
                    self.handle_event(event)
                self.update(dt)
                self.draw()
                self.present()
        finally:
            if self.game:
                self.record_game()
            self.persist_settings()
            pygame.quit()


def main():
    parser = argparse.ArgumentParser(description='NERV Crisis')
    parser.add_argument('--skip-intro', action='store_true', help='Skip the logo splash (resources still load)')
    parser.add_argument('--windowed', action='store_true', help='Start in a resizable window instead of fullscreen')
    args = parser.parse_args()
    Menu(skip_intro=args.skip_intro, fullscreen=not args.windowed).run()


if __name__ == '__main__':
    main()
