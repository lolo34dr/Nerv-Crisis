import pygame
import sys
import math
import random
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

from engine.game import variable

pygame.init()
# Le menu reste utilisable sans périphérique audio.
if not pygame.mixer.get_init():
    try:
        pygame.mixer.init()
    except pygame.error:
        pass
AUDIO_AVAILABLE = pygame.mixer.get_init() is not None

class SilentSound:
    def play(self):
        pass

# ---------------------------
# Dimensions et affichage
# ---------------------------
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.RESIZABLE)
pygame.display.set_caption("Neon Genesis - NERV Crisis")
pygame.display.set_icon(pygame.image.load(str(ROOT / "engine/images/icon.jpg")))
# F11 permet de basculer en plein écran depuis le menu.

# ---------------------------
# Chargement des polices
# ---------------------------
pixel_font_large = pygame.font.Font(variable.pixel_font, 32)
pixel_font_medium = pygame.font.Font(variable.pixel_font, 24)
pixel_font_small = pygame.font.Font(variable.pixel_font, 16)
pixel_font_title = pygame.font.Font(variable.pixel_font, 64)
pixel_font_copyright = pygame.font.Font(variable.pixel_font, 28)

# ---------------------------
# Couleurs et palettes
# ---------------------------
COLORS = {
    "bg_top": (10, 10, 30),
    "bg_bottom": (0, 0, 0),
    "neon_cyan": (0, 255, 255),
    "neon_pink": (255, 0, 255),
    "glow": (100, 255, 255),
    "text": (200, 220, 255),
    "scanline": (0, 0, 0, 50)
}

# ---------------------------
# Musique et effets sonores
# ---------------------------
if AUDIO_AVAILABLE:
    pygame.mixer.music.load(variable.opening_music)
    pygame.mixer.music.set_volume(0.6)
hover_sound = pygame.mixer.Sound(variable.over_soundeffect) if AUDIO_AVAILABLE else SilentSound()
click_sound = pygame.mixer.Sound(variable.start_soundeffect) if AUDIO_AVAILABLE else SilentSound()

# ---------------------------
# Chargement et traitement de l'image Evangelion
# ---------------------------
evangelion_img = pygame.image.load(str(ROOT / "engine/images/evangelion.png"))
evangelion_img = pygame.transform.scale(evangelion_img, (300, 300))

def create_rounded_mask(surface, radius):
    mask = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255), mask.get_rect(), border_radius=radius)
    return mask

rounded_mask = create_rounded_mask(evangelion_img, 15)
evangelion_img_rounded = pygame.Surface(evangelion_img.get_size(), pygame.SRCALPHA)
evangelion_img_rounded.blit(evangelion_img, (0, 0))
evangelion_img_rounded.blit(rounded_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

# ---------------------------
# Création d'un fond en dégradé
# ---------------------------
def create_gradient_surface(width, height, top_color, bottom_color):
    gradient = pygame.Surface((width, height))
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        pygame.draw.line(gradient, (r, g, b), (0, y), (width, y))
    return gradient

gradient_bg = create_gradient_surface(SCREEN_WIDTH, SCREEN_HEIGHT, COLORS["bg_top"], COLORS["bg_bottom"])

# ---------------------------
# Création d'une surface de lignes cybernétiques (générée une seule fois)
# ---------------------------
def generate_cyber_lines_surface():
    surface = pygame.Surface((SCREEN_WIDTH * 2, SCREEN_HEIGHT), pygame.SRCALPHA)
    for i in range(200):
        x = random.randint(0, SCREEN_WIDTH * 2)
        y = random.randint(0, SCREEN_HEIGHT)
        length = random.randint(50, 250)
        color_choice = random.choice([(0, 150, 255), (255, 0, 255)])
        angle = i / 10
        pygame.draw.line(
            surface,
            (*color_choice, 50),
            (x, y),
            (x + length * math.cos(angle), y + length * math.sin(angle)),
            random.randint(1, 3)
        )
    return surface

cyber_lines_surface = generate_cyber_lines_surface()
cyber_offset = 0

# ---------------------------
# Fonctions d'effets visuels
# ---------------------------
def draw_glow(surface, pos, radius, color):
    for i in range(10, 0, -1):
        glow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        alpha = int(50 * (i / 10))
        pygame.draw.circle(glow_surf, (*color, alpha), (radius, radius), int(radius * (i / 10)))
        surface.blit(glow_surf, (pos[0] - radius, pos[1] - radius), special_flags=pygame.BLEND_RGBA_ADD)

def render_text(font, text, color, glow=False):
    text_surface = font.render(text, True, color)
    if not glow:
        return text_surface
    final_surface = pygame.Surface((text_surface.get_width() + 8, text_surface.get_height() + 8), pygame.SRCALPHA)
    shadow = font.render(text, True, (0, 0, 0))
    final_surface.blit(shadow, (4, 4))
    for offset in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        glow_layer = font.render(text, True, COLORS["neon_pink"])
        final_surface.blit(glow_layer, (offset[0] + 4, offset[1] + 4))
    final_surface.blit(text_surface, (4, 4))
    return final_surface

def render_text_with_unicode(font, text, color, glow=False):
    text = text.replace("©", "\u00A9")
    return render_text(font, text, color, glow)

# ---------------------------
# Écran de chargement (warning)
# ---------------------------
def loading_screen():
    running = True
    clock_local = pygame.time.Clock()
    countdown = 5
    start_ticks = pygame.time.get_ticks()
    while running:
        screen.blit(gradient_bg, (0, 0))
        warning_text = render_text(pixel_font_large, "WARNING", COLORS["text"])
        warning_rect = warning_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        screen.blit(warning_text, warning_rect)
        detailed_warning = (
            "This game may contain photosensitive effects.\n"
            "If you're sensitive to flashing lights,\n"
            "please take precautions."
        )
        detailed_warning_text = render_text(pixel_font_medium, detailed_warning, COLORS["text"])
        detailed_rect = detailed_warning_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        screen.blit(detailed_warning_text, detailed_rect)
        seconds_passed = (pygame.time.get_ticks() - start_ticks) // 1000
        if seconds_passed < countdown:
            countdown_text = render_text(pixel_font_medium, f"Starting in {countdown - seconds_passed}...", COLORS["text"])
            countdown_rect = countdown_text.get_rect(center=(SCREEN_WIDTH // 2, int(SCREEN_HEIGHT // 1.5)))
            screen.blit(countdown_text, countdown_rect)
        else:
            break
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        clock_local.tick(60)

# ---------------------------
# Fonctions de fondu
# ---------------------------
def fade_in_out(surface, fade_in=True, fade_speed=5):
    fade_surface_local = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    fade_surface_local.fill((0, 0, 0))
    alpha_range = range(0, 256, fade_speed) if fade_in else range(255, -1, -fade_speed)
    for alpha in alpha_range:
        fade_surface_local.set_alpha(alpha)
        screen.blit(surface, (0, 0))
        screen.blit(fade_surface_local, (0, 0))
        pygame.display.flip()
        pygame.time.delay(10)

# ---------------------------
# Animation du logo
# ---------------------------
def animate_logo():
    logo = pygame.image.load(str(ROOT / "engine/images/icon.jpg"))
    logo = pygame.transform.scale(logo, (500, 500))
    logo_surface = pygame.Surface(logo.get_size(), pygame.SRCALPHA)
    mask = create_rounded_mask(logo, 15)
    logo_surface.blit(logo, (0, 0))
    logo_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pos_x = (SCREEN_WIDTH - logo_surface.get_width()) // 2
    pos_y = (SCREEN_HEIGHT - logo_surface.get_height()) // 2
    for alpha in range(0, 256, 5):
        logo_surface.set_alpha(alpha)
        screen.fill(COLORS["bg_bottom"])
        screen.blit(logo_surface, (pos_x, pos_y))
        pygame.display.flip()
        pygame.time.delay(30)
    pygame.time.delay(500)
    for alpha in range(255, -1, -5):
        logo_surface.set_alpha(alpha)
        screen.fill(COLORS["bg_bottom"])
        screen.blit(logo_surface, (pos_x, pos_y))
        pygame.display.flip()
        pygame.time.delay(30)

# ---------------------------
# Boîte de confirmation pour Quit
# ---------------------------
def confirm_quit():
    confirm_running = True
    confirm_clock = pygame.time.Clock()
    while confirm_running:
        confirm_clock.tick(60)
        screen.blit(gradient_bg, (0, 0))
        confirm_text = render_text(pixel_font_large, "Are you sure you want to quit?", COLORS["text"], glow=True)
        confirm_rect = confirm_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        screen.blit(confirm_text, confirm_rect)
        yes_button = render_text(pixel_font_medium, "Yes", COLORS["neon_cyan"], glow=True)
        no_button = render_text(pixel_font_medium, "No", COLORS["neon_cyan"], glow=True)
        yes_rect = yes_button.get_rect(center=(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2))
        no_rect = no_button.get_rect(center=(SCREEN_WIDTH // 2 + 100, SCREEN_HEIGHT // 2))
        screen.blit(yes_button, yes_rect)
        screen.blit(no_button, no_rect)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_y):
                    return True
                if event.key in (pygame.K_ESCAPE, pygame.K_n):
                    return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if yes_rect.collidepoint(event.pos):
                    return True
                if no_rect.collidepoint(event.pos):
                    return False
        pygame.display.update()

# ---------------------------
# Écran de chargement style Evangelion
# ---------------------------
def evangelion_loading_screen():
    running = True
    clock_local = pygame.time.Clock()
    start_time = pygame.time.get_ticks()
    progress = 0
    rotation_angle = 0
    nerv_radius = 80

    nerv_logo = [
        (0, -1), (0.5, -0.5), (1, -1),
        (1, 1), (0.5, 0.5), (0, 1),
        (-0.5, 0.5), (-1, 1), (-1, -1),
        (-0.5, -0.5), (0, -1)
    ]

    status_messages = [
        "INITIALIZING LCL SYSTEM...",
        "SYNCHRONIZING PILOT/EVA...",
        "CHECKING POSITRON RIFLE...",
        "LOADING COMBAT PROTOCOLS...",
        "CALCULATING SYNCHRONIZATION PARAMETERS...",
        "CONNECTING TO THE MAGI...",
        "MONITORING A10 NERVE CONNECTIONS...",
        "AT FIELD GENERATOR: ONLINE..."
    ]

    while running:
        dt = clock_local.tick(60) / 1000
        rotation_angle = (rotation_angle + dt * 45) % 360
        elapsed = pygame.time.get_ticks() - start_time
        progress = min(elapsed / 10000, 1.0)  # 10 secondes

        screen.blit(gradient_bg, (0, 0))

        nerv_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3)
        scaled_logo = [(x * nerv_radius + nerv_pos[0], y * nerv_radius + nerv_pos[1])
                       for x, y in nerv_logo]
        pygame.draw.polygon(screen, COLORS["neon_pink"], scaled_logo, 3)

        num_lines = 12
        for i in range(num_lines):
            angle_rad = math.radians(rotation_angle + (i * 360 / num_lines))
            end_pos = (
                nerv_pos[0] + math.cos(angle_rad) * nerv_radius * 1.5,
                nerv_pos[1] + math.sin(angle_rad) * nerv_radius * 1.5
            )
            pygame.draw.line(screen, COLORS["neon_cyan"], nerv_pos, end_pos, 2)

        bar_width = 600
        bar_height = 20
        bar_rect = pygame.Rect((SCREEN_WIDTH - bar_width) // 2, SCREEN_HEIGHT // 2, bar_width, bar_height)
        pygame.draw.rect(screen, COLORS["neon_cyan"], bar_rect.inflate(10, 10), 3, border_radius=5)
        fill_width = int(bar_width * progress)
        fill_rect = pygame.Rect(bar_rect.left + 5, bar_rect.top + 5, max(fill_width - 10, 0), bar_height - 10)
        pygame.draw.rect(screen, COLORS["neon_pink"], fill_rect, border_radius=5)

        percent_text = render_text(pixel_font_large, f"{int(progress * 100)}%", COLORS["neon_cyan"], glow=True)
        percent_rect = percent_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
        screen.blit(percent_text, percent_rect)

        status_index = int(progress * len(status_messages))
        if status_index < len(status_messages):
            status_text = render_text(pixel_font_small, status_messages[status_index], COLORS["text"])
            status_rect = status_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))
            screen.blit(status_text, status_rect)

        code_text = render_text(pixel_font_small, "0x" + " ".join(f"{random.randint(0,255):02X}" for _ in range(20)), COLORS["text"])
        code_y = (pygame.time.get_ticks() // 50) % SCREEN_HEIGHT
        code_rect = code_text.get_rect(topleft=(0, code_y))
        screen.blit(code_text, code_rect)
        screen.blit(code_text, (0, code_y - SCREEN_HEIGHT))

        jp_text = render_text(pixel_font_medium, "Starting Up", COLORS["neon_pink"], glow=True)
        jp_rect = jp_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100))
        screen.blit(jp_text, jp_rect)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        if progress >= 1.0:
            running = False

# ---------------------------
# Fonction Game Selector (pour "New Game")
# ---------------------------
def game_selector():
    """
    Affiche une liste de jeux disponibles.
    - 'Shooter' lance le script engine/game/shooter.py
    - 'Back' revient au menu principal
    La navigation se fait avec les touches UP/DOWN ET avec la souris.
    """
    selector_running = True
    selector_clock = pygame.time.Clock()
    selected_index = 0
    game_options = [
        {"text": "Shooter", "action": "shooter"},
        {"text": "Back", "action": "back"}
    ]
    # Pré-calcul des surfaces et rectangles pour chaque option
    option_surfaces = []
    option_rects = []
    for i, opt in enumerate(game_options):
        surf = render_text(pixel_font_medium, opt["text"], COLORS["text"], glow=True)
        rect = surf.get_rect(center=(SCREEN_WIDTH // 2, 200 + i * 60))
        option_surfaces.append(surf)
        option_rects.append(rect)

    while selector_running:
        selector_clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            # Gestion des événements clavier
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key == pygame.K_UP:
                    selected_index = (selected_index - 1) % len(game_options)
                elif event.key == pygame.K_DOWN:
                    selected_index = (selected_index + 1) % len(game_options)
                elif event.key == pygame.K_RETURN:
                    chosen = game_options[selected_index]
                    if chosen["action"] == "shooter":
                        subprocess.Popen([sys.executable, "-m", "engine.game.shooter"], cwd=ROOT)
                        selector_running = False
                    elif chosen["action"] == "back":
                        selector_running = False
            # Gestion des événements souris
            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, rect in enumerate(option_rects):
                    if rect.collidepoint(event.pos):
                        selected_index = i
                        chosen = game_options[selected_index]
                        if chosen["action"] == "shooter":
                            subprocess.Popen([sys.executable, "-m", "engine.game.shooter"], cwd=ROOT)
                            selector_running = False
                        elif chosen["action"] == "back":
                            selector_running = False

        # Affichage du sélecteur
        screen.blit(gradient_bg, (0, 0))
        selector_title = render_text(pixel_font_large, "Select Game", COLORS["text"], glow=True)
        title_rect = selector_title.get_rect(center=(SCREEN_WIDTH // 2, 100))
        screen.blit(selector_title, title_rect)

        # Affichage des options et surlignage de celle sélectionnée
        for i, (surf, rect) in enumerate(zip(option_surfaces, option_rects)):
            if i == selected_index:
                pygame.draw.rect(screen, COLORS["neon_cyan"], rect.inflate(20, 10), 2, border_radius=5)
            screen.blit(surf, rect)

        # Appliquer l'effet CRT et mettre à jour l'affichage
        screen.blit(crt_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.display.flip()
# ---------------------------
# Menu principal
# ---------------------------
menu_items = [
    {"text": "New Game", "pos": (100, 300), "action": "start"},
    {"text": "Load", "pos": (100, 400), "action": "load"},
    {"text": "Lab", "pos": (100, 500), "action": "lab"},
    {"text": "Quit", "pos": (100, 600), "action": "quit"}
]

# ---------------------------
# Préparation de l'écran CRT (effet scanlines)
# ---------------------------
crt_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
for y in range(0, SCREEN_HEIGHT, 2):
    pygame.draw.line(crt_overlay, COLORS["scanline"], (0, y), (SCREEN_WIDTH, y))
for _ in range(2000):
    x = random.randrange(SCREEN_WIDTH)
    y = random.randrange(SCREEN_HEIGHT)
    crt_overlay.set_at((x, y), (*random.choice([(255,255,255), (0,255,0)]), random.randint(10, 30)))

# ---------------------------
# Écrans et transitions avant le menu
# ---------------------------
if "--skip-intro" not in sys.argv:
    fade_in_out(gradient_bg, fade_in=True)
    loading_screen()
    evangelion_loading_screen()
    animate_logo()
    fade_in_out(gradient_bg, fade_in=False)
if AUDIO_AVAILABLE:
    pygame.mixer.music.play(-1)

music_paused = False
volume = 0.6
running = True
clock = pygame.time.Clock()
selected_index = 0
panel = None
notice = ""
notice_until = 0
menu_rects = [pygame.Rect(90, item["pos"][1] - 12, 460, 72) for item in menu_items]
audio_rect = pygame.Rect(700, 590, 490, 74)


def label(text, pos, color=None, font=None):
    surface = (font or pixel_font_small).render(text, True, color or COLORS["text"])
    screen.blit(surface, pos)


def toggle_music():
    global music_paused
    music_paused = not music_paused
    if AUDIO_AVAILABLE:
        if music_paused:
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()


def activate(index):
    global running, panel, notice, notice_until
    click_sound.play()
    action = menu_items[index]["action"]
    if action == "start":
        game_selector()
    elif action == "quit":
        if confirm_quit():
            running = False
    elif action == "lab":
        panel = "lab"
    elif action == "load":
        notice = "Aucune sauvegarde : lancez New Game."
        notice_until = pygame.time.get_ticks() + 4000


while running:
    dt = min(clock.tick(60) / 1000, .1)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if confirm_quit():
                running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
            elif event.key == pygame.K_m:
                toggle_music()
            elif panel:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                    panel = None
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    volume = max(0, min(1, round(volume + (.1 if event.key == pygame.K_RIGHT else -.1), 1)))
                    if AUDIO_AVAILABLE:
                        pygame.mixer.music.set_volume(volume)
            elif event.key in (pygame.K_UP, pygame.K_DOWN):
                selected_index = (selected_index + (1 if event.key == pygame.K_DOWN else -1)) % len(menu_items)
                hover_sound.play()
            elif event.key == pygame.K_RETURN:
                activate(selected_index)
            elif event.key == pygame.K_ESCAPE:
                if confirm_quit():
                    running = False
        elif event.type == pygame.MOUSEMOTION and not panel:
            for index, rect in enumerate(menu_rects):
                if rect.collidepoint(event.pos) and selected_index != index:
                    selected_index = index
                    hover_sound.play()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if panel:
                panel = None
            elif audio_rect.collidepoint(event.pos):
                toggle_music()
            else:
                for index, rect in enumerate(menu_rects):
                    if rect.collidepoint(event.pos):
                        selected_index = index
                        activate(index)
                        break

    screen.blit(gradient_bg, (0, 0))
    cyber_offset = (cyber_offset + 60 * dt) % SCREEN_WIDTH
    screen.blit(cyber_lines_surface, (-cyber_offset, 0))
    # Cadre de commande MAGI et signature visuelle du menu historique.
    pygame.draw.rect(screen, (12, 22, 40), (60, 245, 520, 450), border_radius=18)
    pygame.draw.rect(screen, (35, 75, 95), (60, 245, 520, 450), 1, border_radius=18)
    title = render_text(pixel_font_title, "NERV Crisis", COLORS["neon_cyan"], glow=True)
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 125)))
    label("MAGI SYSTEM / COMBAT OPERATIONS", (395, 190), COLORS["neon_pink"])
    label("01 / PILOT TERMINAL", (90, 260), COLORS["neon_cyan"])
    subtitles = ["Lancer une nouvelle mission", "Sauvegardes non disponibles", "Audio et commandes", "Fermer le terminal"]
    for index, (item, rect) in enumerate(zip(menu_items, menu_rects)):
        active = index == selected_index
        if active:
            pygame.draw.rect(screen, (18, 48, 65), rect, border_radius=8)
            pygame.draw.rect(screen, COLORS["neon_cyan"], rect, 2, border_radius=8)
            pygame.draw.rect(screen, COLORS["neon_pink"], (rect.x, rect.y + 12, 4, rect.h - 24))
        label(item["text"], (rect.x + 18, rect.y + 7), COLORS["neon_cyan"] if active else COLORS["text"], pixel_font_medium)
        label(subtitles[index], (rect.x + 18, rect.y + 43), (135, 160, 185))
    pulse = int(100 + 70 * math.sin(pygame.time.get_ticks() / 700))
    pygame.draw.rect(screen, (0, pulse, pulse), (790, 258, 320, 320), 2, border_radius=20)
    screen.blit(evangelion_img_rounded, (800, 268))
    label("EVA / SYNCHRONIZATION ONLINE", (745, 225), COLORS["neon_cyan"])
    pygame.draw.rect(screen, (18, 35, 52), audio_rect, border_radius=10)
    pygame.draw.rect(screen, COLORS["neon_cyan"], audio_rect, 1, border_radius=10)
    label("The Cruel Angel's Thesis", (audio_rect.x + 18, audio_rect.y + 12))
    status = "PAUSE" if music_paused else "LECTURE"
    if not AUDIO_AVAILABLE:
        status = "AUDIO INDISPONIBLE"
    label(status + " / M : musique", (audio_rect.x + 18, audio_rect.y + 40), COLORS["neon_cyan"])
    if pygame.time.get_ticks() < notice_until:
        label(notice, (90, 705), COLORS["neon_pink"])
    label("FLECHES / ENTREE : choisir    M : musique    F11 : plein ecran", (135, 742))
    label("COPYRIGHT 2025 0-cyz-0", (490, 775), (110, 135, 160))
    if panel:
        shade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 12, 220))
        screen.blit(shade, (0, 0))
        pygame.draw.rect(screen, (15, 25, 45), (240, 200, 800, 400), border_radius=16)
        pygame.draw.rect(screen, COLORS["neon_cyan"], (240, 200, 800, 400), 2, border_radius=16)
        label("LAB / REGLAGES", (290, 235), COLORS["neon_cyan"], pixel_font_large)
        label(f"Volume musique : {round(volume * 100)}%  /  Fleches gauche-droite", (290, 310))
        pygame.draw.rect(screen, (40, 60, 80), (290, 350, 680, 10), border_radius=5)
        pygame.draw.rect(screen, COLORS["neon_pink"], (290, 350, round(680 * volume), 10), border_radius=5)
        label("Jeu : fleches / ZQSD / WASD, ESPACE pour tirer", (290, 400))
        label("P : pause du jeu   /   M : musique du menu", (290, 445))
        label("ENTREE, ECHAP ou clic : retour", (290, 535), COLORS["neon_cyan"])
    pygame.display.flip()

pygame.quit()
sys.exit()
