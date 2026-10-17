"""Exercise the historical menu and its connection to the improved shooter."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import pygame

ROOT = Path(__file__).resolve().parents[1]


class MenuTests(unittest.TestCase):
    def test_original_menu_launches_shooter_and_quits(self):
        events = [
            [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(110, 310), button=1)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)],
            [pygame.event.Event(pygame.QUIT)],
            [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(540, 400), button=1)],
        ]
        with patch.object(sys, 'argv', [str(ROOT / 'main.py'), '--skip-intro']), \
                patch('pygame.event.get', side_effect=events), \
                patch('subprocess.Popen') as launch:
            with self.assertRaises(SystemExit):
                runpy.run_path(str(ROOT / 'main.py'), run_name='__main__')
        launch.assert_called_once_with(
            [sys.executable, '-m', 'engine.game.shooter'], cwd=ROOT)
        self.assertFalse(pygame.get_init())
