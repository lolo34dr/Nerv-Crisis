"""NERV terminal: original artwork and soundtrack, with a scalable interface."""
import argparse
import math
import subprocess
import sys
from pathlib import Path

import pygame

from engine.game import variable

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
    def __init__(self, skip_intro=False):
        pygame.init()
        desktop = pygame.display.get_desktop_sizes()[0]
        self.window = pygame.display.set_mode(
            (min(SIZE[0], desktop[0]), min(SIZE[1], desktop[1])), pygame.RESIZABLE)
        pygame.display.set_caption('NERV Crisis / Pilot terminal')
        self.canvas = pygame.Surface(SIZE)
        self.logo = pygame.image.load(str(variable.ASSETS / 'images/icon.png')).convert_alpha()
        pygame.display.set_icon(self.logo)
        self.logo_small = pygame.transform.smoothscale(self.logo, (44, 44))
        # Keep the supplied illustration square, without stretching or cropping it.
        art = pygame.image.load(str(variable.ASSETS / 'images/evangelion.png')).convert_alpha()
        self.art = pygame.transform.smoothscale(art, (384, 384))
        self.fonts = {size: pygame.font.Font(variable.pixel_font, size) for size in (16, 20, 28, 52, 62)}
        self.body_fonts = {size: pygame.font.Font(None, size) for size in (20, 24, 28, 32)}
        self.clock = pygame.time.Clock()
        self.running = True
        self.selected = 0
        self.modal = None
        self.modal_selected = 0
        self.music_paused = False
        self.volume = .6
        self.dragging_volume = False
        self.fullscreen = False
        self.window_size = self.window.get_size()
        self.child = None
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
        self.audio_available = pygame.mixer.get_init() is not None
        self.hover_sound = None
        self.click_sound = None
        if self.audio_available:
            try:
                pygame.mixer.music.load(variable.opening_music)
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.play(-1)
                self.hover_sound = pygame.mixer.Sound(variable.over_soundeffect)
                self.click_sound = pygame.mixer.Sound(variable.start_soundeffect)
                self.hover_sound.set_volume(.25)
                self.click_sound.set_volume(.35)
            except pygame.error:
                self.audio_available = False
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
        self.window.fill((3, 6, 12))
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
        self.sync_music()

    def sync_music(self):
        if self.audio_available:
            if self.music_paused or self.child is not None:
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.unpause()

    def set_volume(self, volume):
        self.volume = max(0, min(1, round(volume, 2)))
        if self.audio_available:
            pygame.mixer.music.set_volume(self.volume)

    def open_modal(self, kind):
        self.modal = kind
        self.modal_selected = 1 if kind == 'quit' else 0
        self.dragging_volume = False

    def activate(self, index):
        self.sound(self.click_sound)
        self.open_modal(('selector', 'load', 'lab', 'quit')[index])

    def launch_game(self):
        if self.child is not None:
            return
        try:
            self.child = subprocess.Popen([sys.executable, '-m', 'engine.game.shooter'], cwd=ROOT)
            self.sync_music()
            self.modal = None
        except OSError:
            self.notice = 'Le jeu ne peut pas démarrer. Vérifiez votre installation Python.'
            self.notice_until = pygame.time.get_ticks() + 5000

    def modal_action(self, index):
        if self.modal == 'quit':
            if index == 0:
                self.running = False
            else:
                self.modal = None
        elif self.modal == 'selector' and index == 0:
            self.launch_game()
        elif self.modal == 'load' and index == 0:
            self.open_modal('selector')
        elif self.modal == 'lab' and index == 0:
            self.toggle_music()
        else:
            self.modal = None

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            self.dragging_volume = False
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
            if event.key == pygame.K_m:
                self.toggle_music()
            elif self.modal:
                if event.key == pygame.K_ESCAPE:
                    self.modal = None
                    self.dragging_volume = False
                elif self.modal == 'lab' and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    self.set_volume(self.volume + (.1 if event.key == pygame.K_RIGHT else -.1))
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
                    self.modal_selected = 1 - self.modal_selected
                elif event.key == pygame.K_RETURN:
                    self.modal_action(self.modal_selected)
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
                self.selected = (self.selected + (-1 if event.key == pygame.K_UP else 1)) % 4
                self.sound(self.hover_sound)
            elif event.key == pygame.K_RETURN:
                self.activate(self.selected)
            elif event.key == pygame.K_ESCAPE:
                self.open_modal('quit')
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_volume = False
        if event.type not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            return
        pos = self.logical_position(event.pos)
        if pos is None:
            return
        click = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
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
            else:
                for index, rect in enumerate(self.modal_buttons):
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
        if click and self.music_rect.collidepoint(pos):
            self.toggle_music()

    def update(self, dt):
        self.time += dt
        if self.intro:
            self.intro_elapsed += dt
            if self.intro_elapsed >= 3:
                self.intro = False
        if self.child is not None:
            code = self.child.poll()
            if code is not None:
                self.child = None
                self.sync_music()
                if code:
                    self.notice = 'Le jeu s’est arrêté avec une erreur. Consultez le terminal.'
                    self.notice_until = pygame.time.get_ticks() + 5000

    def draw_header(self):
        self.canvas.blit(self.logo_small, (64, 30))
        self.text('NERV', (124, 33), 28, pixel=True)
        self.text('PILOT TERMINAL / TOKYO-3', (126, 65), 20, MUTED)
        self.card(pygame.Rect(1010, 38, 206, 36), border=(45, 92, 83), radius=18)
        pygame.draw.circle(self.canvas, CYAN, (1030, 56), 4)
        self.text('MAGI SYSTEM ONLINE', (1044, 47), 20, CYAN)
        pygame.draw.line(self.canvas, BORDER, (64, 102), (1216, 102))

    def draw(self):
        self.canvas.blit(self.background, (0, 0))
        self.draw_header()
        if self.intro:
            self.draw_intro()
            return
        self.text('OPÉRATIONS / 01', (64, 140), 20, CYAN)
        self.text('NERV', (60, 171), 62, pixel=True)
        self.text('CRISIS', (262, 171), 62, CYAN, pixel=True)
        self.text('Prenez les commandes. Protégez la base.', (66, 252), 28, MUTED)
        names = ('New Game', 'Load', 'Lab', 'Quit')
        descriptions = ('Déployer une nouvelle mission', 'Informations sur les sauvegardes',
                        'Réglages audio et commandes', 'Fermer le terminal')
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
        if self.music_paused or self.child is not None:
            pygame.draw.polygon(self.canvas, CYAN, [(763, 677), (763, 695), (776, 686)])
        else:
            for x in (762, 770):
                pygame.draw.rect(self.canvas, CYAN, (x, 678, 4, 16), border_radius=1)
        self.text("The Cruel Angel's Thesis", (802, 655), 28)
        status = 'En pause' if self.music_paused else 'Lecture en boucle'
        if self.child is not None:
            status = 'Musique du jeu active'
        if not self.audio_available:
            status = 'Sortie audio indisponible'
        self.text(status + '  ·  M : pause', (802, 691), 24, MUTED)
        for index in range(12):
            height = (7 + int(10 * (1 + math.sin(self.time * 4 + index)))) if not self.music_paused and self.child is None and self.audio_available else 4
            pygame.draw.rect(self.canvas, CYAN, (1136 + index * 4, 709 - height, 2, height))
        self.text('SURVIE ARCADE', (66, 698), 20, CYAN)
        self.text('3 vies. Des vagues infinies. Une seule mission.', (66, 722), 24, MUTED)
        pygame.draw.line(self.canvas, BORDER, (64, 754), (1216, 754))
        self.text('Flèches : choisir     Entrée  Valider     M  Musique     F11  Plein écran', (64, 770), 20, MUTED)
        self.text('© 2025 0-cyz-0', (1092, 770), 20, MUTED)
        if self.notice and pygame.time.get_ticks() < self.notice_until:
            self.card(pygame.Rect(224, 690, 832, 52), border=PINK)
            self.paragraph(self.notice, pygame.Rect(244, 704, 792, 32), 24, TEXT)
        if self.modal:
            self.draw_modal()

    def draw_intro(self):
        logo = pygame.transform.smoothscale(self.logo, (200, 200))
        self.canvas.blit(logo, (540, 160))
        self.text('NERV CRISIS', (426, 390), 52, CYAN, pixel=True)
        self.paragraph('Initialisation du terminal de combat.\nCertains effets visuels peuvent gêner les personnes photosensibles.',
                       pygame.Rect(350, 480, 580, 110), 28)
        pygame.draw.rect(self.canvas, BORDER, (350, 612, 580, 4))
        pygame.draw.rect(self.canvas, CYAN, (350, 612, int(580 * min(1, self.intro_elapsed / 3)), 4))
        self.text('Entrée / Espace / clic : passer', (485, 660), 24, MUTED)

    def draw_modal(self):
        shade = pygame.Surface(SIZE, pygame.SRCALPHA)
        shade.fill((2, 6, 14, 225))
        self.canvas.blit(shade, (0, 0))
        self.card(pygame.Rect(260, 170, 760, 460), (17, 27, 41), BORDER, 20)
        titles = {'selector': 'CHOISIR UNE MISSION', 'lab': 'LAB / AUDIO',
                  'load': 'SAUVEGARDES', 'quit': 'QUITTER LE TERMINAL ?'}
        self.text(titles[self.modal], (308, 211), 28, CYAN, pixel=True)
        self.card(self.close_rect, border=BORDER, radius=8)
        self.text('×', (937, 201), 32, MUTED)
        pygame.draw.line(self.canvas, BORDER, (308, 266), (972, 266))
        if self.modal == 'lab':
            self.text('Volume de la musique', (308, 301), 28)
            self.text(f'{round(self.volume * 100):3d} %', (902, 301), 28, CYAN)
            pygame.draw.rect(self.canvas, BORDER, (308, 364, 664, 4), border_radius=2)
            pygame.draw.rect(self.canvas, CYAN, (308, 364, round(664 * self.volume), 4), border_radius=2)
            pygame.draw.circle(self.canvas, CYAN, (308 + round(664 * self.volume), 366), 8)
            self.paragraph('Glissez le curseur ou utilisez gauche / droite.\nJeu : flèches / ZQSD / WASD · Espace : tirer · P : pause.',
                           pygame.Rect(308, 404, 664, 74), 24)
            buttons = ('Musique : ' + ('pause' if self.music_paused else 'lecture'), 'Retour')
        else:
            descriptions = {
                'selector': 'SHOOTER / Défense de Tokyo-3\nDétruisez les ennemis et protégez la base. Trois vies, des vagues toujours plus rapides.',
                'load': 'Aucune sauvegarde disponible.\nLes parties sont jouées en une session. Choisissez New Game pour lancer une mission.',
                'quit': 'Voulez-vous fermer NERV Crisis ?\nVous pourrez revenir au terminal en relançant le jeu.'}
            self.paragraph(descriptions[self.modal], pygame.Rect(308, 305, 664, 145), 28)
            buttons = {'selector': ('Lancer Shooter', 'Retour'), 'load': ('Nouvelle partie', 'Retour'),
                       'quit': ('Quitter', 'Annuler')}[self.modal]
        for index, (rect, title) in enumerate(zip(self.modal_buttons, buttons)):
            active = index == self.modal_selected
            self.card(rect, (22, 54, 58) if active else PANEL, CYAN if active else BORDER, 10)
            font = self.body_fonts[28]
            self.text(title, (rect.centerx - font.size(title)[0] // 2, rect.y + 21), 28, CYAN if active else TEXT)
        self.text('Entrée : valider     Échap : retour', (308, 586), 24, MUTED)

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
            pygame.quit()


def main():
    parser = argparse.ArgumentParser(description='NERV Crisis')
    parser.add_argument('--skip-intro', action='store_true', help='Ouvrir directement le menu')
    Menu(skip_intro=parser.parse_args().skip_intro).run()


if __name__ == '__main__':
    main()
