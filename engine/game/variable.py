"""Configuration without display initialization or working-directory assumptions."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'engine'
WIDTH, HEIGHT = 960, 640
BLACK = (8, 10, 22)
TEXT_COLOR = (225, 235, 245)
HIGHLIGHT_COLOR = (255, 195, 70)
pixel_font = str(ASSETS / 'font' / 'pixel.ttf')
opening_music = str(ASSETS / 'audio' / '残酷な天使のテーゼ.mp3')
over_soundeffect = str(ASSETS / 'audio' / 'select.mp3')
start_soundeffect = str(ASSETS / 'audio' / 'selected.mp3')
