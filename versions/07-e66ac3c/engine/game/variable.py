import pygame

pygame.init()

# ===================================
#           Music Variable          
# ===================================

opening_music = "engine/audio/残酷な天使のテーゼ.mp3"
over_soundeffect = "engine/audio/select.mp3"
start_soundeffect = "engine/audio/selected.mp3"

# ===================================
#           Font Variable          
# ===================================

pixel_font = "engine/font/pixel.ttf"

# ===================================
#           Image Variable          
# ===================================

background_image = "engine/images/background.png"

# ===================================
#           Screen Variable          
# ===================================

SCREEN_WIDTH_SET = pygame.display.Info().current_w
SCREEN_HEIGHT_SET = pygame.display.Info().current_h

# ===================================
#           Color Variable          
# ===================================

BLACK = (0, 0, 0)
TEXT_COLOR = (255, 255, 255)
HIGHLIGHT_COLOR = (255, 215, 0)
