import pygame
import sys
import random
import os
import math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from engine.game import variable


pygame.init()
pygame.mixer.init()

# ---------------------------
# Dimensions et affichage
# ---------------------------
SCREEN_WIDTH = variable.SCREEN_WIDTH_SET
SCREEN_HEIGHT = variable.SCREEN_HEIGHT_SET
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Shooter - NERV Crisis")
pygame.display.set_icon(pygame.image.load("engine/images/icon.jpg"))

# ---------------------------
# Chargement des polices
# ---------------------------
pixel_font_large = pygame.font.Font(variable.pixel_font, 32)
pixel_font_medium = pygame.font.Font(variable.pixel_font, 24)
pixel_font_small = pygame.font.Font(variable.pixel_font, 16)

# ---------------------------
# Couleurs et palettes
# ---------------------------
COLORS = {
    "bg_top": (10, 10, 30),
    "bg_bottom": (0, 0, 0),
    "neon_cyan": (0, 255, 255),
    "neon_pink": (255, 0, 255),
    "text": (200, 220, 255)
}

# ---------------------------
# Fond en dégradé
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
# Fonction d'affichage de texte
# ---------------------------
def render_text(font, text, color, glow=False):
    # Ici, un rendu simple est utilisé. Vous pouvez y ajouter des effets de glow si souhaité.
    return font.render(text, True, color)

# ---------------------------
# Classes pour le joueur, les balles et les ennemis
# ---------------------------
class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 50, 50)
        self.speed = 5

    def move(self, dx):
        self.rect.x += dx * self.speed
        if self.rect.x < 0:
            self.rect.x = 0
        if self.rect.x > SCREEN_WIDTH - self.rect.width:
            self.rect.x = SCREEN_WIDTH - self.rect.width

    def draw(self, surface):
        pygame.draw.rect(surface, COLORS["neon_cyan"], self.rect)

class Bullet:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 5, 10)
        self.speed = 7

    def update(self):
        self.rect.y -= self.speed

    def draw(self, surface):
        pygame.draw.rect(surface, COLORS["neon_pink"], self.rect)

class Enemy:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.speed = 2

    def update(self):
        self.rect.y += self.speed

    def draw(self, surface):
        pygame.draw.rect(surface, COLORS["text"], self.rect)

# ---------------------------
# Menu Pause
# ---------------------------
def pause_menu():
    """
    Affiche le menu pause avec les options :
      - Resume : reprendre la partie.
      - Option : (placeholder).
      - Quit Game : quitter le shooter pour revenir au menu principal.
    """
    paused = True
    clock_pause = pygame.time.Clock()
    pause_options = [
        {"text": "Resume", "action": "resume"},
        {"text": "Option", "action": "option"},
        {"text": "Quit Game", "action": "quit"}
    ]
    selected_index = 0

    while paused:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_index = (selected_index - 1) % len(pause_options)
                elif event.key == pygame.K_DOWN:
                    selected_index = (selected_index + 1) % len(pause_options)
                elif event.key == pygame.K_RETURN:
                    chosen = pause_options[selected_index]
                    if chosen["action"] == "resume":
                        paused = False
                    elif chosen["action"] == "option":
                        # Option placeholder – vous pouvez ajouter des réglages ici
                        pass
                    elif chosen["action"] == "quit":
                        return True  # Retourne True pour quitter la partie
        # Affichage du menu pause
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        title_text = render_text(pixel_font_large, "Paused", COLORS["neon_cyan"])
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        screen.blit(title_text, title_rect)

        # Affichage des options
        for i, option in enumerate(pause_options):
            option_text = render_text(pixel_font_medium, option["text"], COLORS["text"])
            option_rect = option_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + i * 40))
            if i == selected_index:
                pygame.draw.rect(screen, COLORS["neon_cyan"], option_rect.inflate(20, 10), 2, border_radius=5)
            screen.blit(option_text, option_rect)
        
        pygame.display.flip()
        clock_pause.tick(60)
    return False

# ---------------------------
# Boucle principale du Shooter
# ---------------------------
def main():
    clock = pygame.time.Clock()
    player = Player(SCREEN_WIDTH // 2 - 25, SCREEN_HEIGHT - 70)
    bullets = []
    enemies = []
    enemy_spawn_timer = 0
    last_shot_time = 0
    shot_cooldown = 300  # millisecondes entre deux tirs
    running = True

    while running:
        dt = clock.tick(60)
        # Gestion des événements
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            player.move(-1)
        if keys[pygame.K_RIGHT]:
            player.move(1)
        if keys[pygame.K_SPACE]:
            current_time = pygame.time.get_ticks()
            if current_time - last_shot_time > shot_cooldown:
                bullet = Bullet(player.rect.centerx - 2, player.rect.y)
                bullets.append(bullet)
                last_shot_time = current_time
        if keys[pygame.K_ESCAPE]:
            # Affichage du menu pause
            if pause_menu():
                running = False

        # Mise à jour des balles
        for bullet in bullets[:]:
            bullet.update()
            if bullet.rect.y < 0:
                bullets.remove(bullet)

        # Apparition des ennemis toutes les 1000 ms
        if pygame.time.get_ticks() - enemy_spawn_timer > 1000:
            enemy_x = random.randint(0, SCREEN_WIDTH - 40)
            enemy = Enemy(enemy_x, -40)
            enemies.append(enemy)
            enemy_spawn_timer = pygame.time.get_ticks()

        # Mise à jour des ennemis
        for enemy in enemies[:]:
            enemy.update()
            if enemy.rect.y > SCREEN_HEIGHT:
                enemies.remove(enemy)
            # Collision avec le joueur
            if enemy.rect.colliderect(player.rect):
                running = False

        # Collision balle / ennemi
        for enemy in enemies[:]:
            for bullet in bullets[:]:
                if enemy.rect.colliderect(bullet.rect):
                    if enemy in enemies:
                        enemies.remove(enemy)
                    if bullet in bullets:
                        bullets.remove(bullet)
                    break

        # Rendu de la scène
        screen.blit(gradient_bg, (0, 0))
        player.draw(screen)
        for bullet in bullets:
            bullet.draw(screen)
        for enemy in enemies:
            enemy.draw(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
