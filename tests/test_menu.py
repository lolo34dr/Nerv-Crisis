"""Exercise real menu state transitions, rendering, and resized mouse coordinates."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import unittest
from unittest.mock import Mock, patch
import pygame
from main import Menu, SIZE


class MenuTests(unittest.TestCase):
    def setUp(self):
        self.menu = Menu(skip_intro=True)

    def tearDown(self):
        pygame.quit()

    def key(self, value):
        self.menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=value))

    def click(self, position):
        viewport = self.menu.viewport()
        position = (viewport.x + round(position[0] * viewport.w / SIZE[0]),
                    viewport.y + round(position[1] * viewport.h / SIZE[1]))
        self.menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=position, button=1))

    def test_keyboard_launches_game_and_prevents_duplicates(self):
        child = Mock()
        child.poll.return_value = None
        with patch('main.subprocess.Popen', return_value=child) as launch:
            self.key(pygame.K_RETURN)
            self.assertEqual(self.menu.modal, 'selector')
            self.key(pygame.K_RETURN)
            self.assertIs(self.menu.child, child)
            self.menu.launch_game()
            launch.assert_called_once()
            self.assertEqual(launch.call_args.args[0][-1], 'engine.game.shooter')
        child.poll.return_value = 0
        with patch('pygame.mixer.music.unpause') as resume:
            self.menu.update(.1)
            self.assertIsNone(self.menu.child)
            resume.assert_called_once()

    def test_lab_volume_clamps_and_music_button(self):
        self.menu.activate(2)
        with patch('pygame.mixer.music.set_volume') as volume:
            self.key(pygame.K_RIGHT)
            self.assertEqual(self.menu.volume, .7)
            volume.assert_called_with(.7)
            self.click(self.menu.slider.midleft)
            self.assertEqual(self.menu.volume, 0)
            viewport = self.menu.viewport()
            position = (viewport.x + round(1000 * viewport.w / SIZE[0]),
                        viewport.y + round(366 * viewport.h / SIZE[1]))
            self.menu.handle_event(pygame.event.Event(pygame.MOUSEMOTION,
                pos=position, rel=(0, 0), buttons=(1, 0, 0)))
            self.assertEqual(self.menu.volume, 1)
        self.menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(1200, 366), button=1))
        self.assertFalse(self.menu.dragging_volume)
        self.key(pygame.K_RETURN)
        self.assertTrue(self.menu.music_paused)
        self.assertEqual(self.menu.modal, 'lab')
        self.key(pygame.K_ESCAPE)
        self.assertIsNone(self.menu.modal)

    def test_resized_letterbox_mapping_and_click_targets(self):
        for size in ((800, 600), (1600, 700), (640, 400)):
            self.menu.window = pygame.display.set_mode(size, pygame.RESIZABLE)
            self.menu.draw()
            self.menu.present()
            self.click(self.menu.menu_rects[0].center)
            self.assertEqual(self.menu.modal, 'selector')
            self.key(pygame.K_ESCAPE)
            self.assertIsNone(self.menu.modal)
        self.menu.window = pygame.display.set_mode((800, 800), pygame.RESIZABLE)
        self.assertIsNone(self.menu.logical_position((0, 0)))

    def test_load_and_quit_confirmation(self):
        self.menu.activate(1)
        self.key(pygame.K_RETURN)
        self.assertEqual(self.menu.modal, 'selector')
        self.key(pygame.K_ESCAPE)
        self.key(pygame.K_ESCAPE)
        self.assertEqual(self.menu.modal, 'quit')
        self.key(pygame.K_RETURN)  # Cancel is selected by default.
        self.assertTrue(self.menu.running)
        self.assertIsNone(self.menu.modal)
        self.key(pygame.K_ESCAPE)
        self.key(pygame.K_LEFT)
        self.key(pygame.K_RETURN)
        self.assertFalse(self.menu.running)

    def test_all_screens_render_and_intro_is_skippable(self):
        self.menu.intro = True
        self.menu.draw()
        self.menu.present()
        self.key(pygame.K_SPACE)
        self.assertFalse(self.menu.intro)
        self.menu.draw()
        for modal in ('selector', 'lab', 'load', 'quit'):
            self.menu.open_modal(modal)
            self.menu.draw()
            self.menu.present()
        self.menu.handle_event(pygame.event.Event(pygame.QUIT))
        self.assertFalse(self.menu.running)

    def test_no_audio_and_launch_failure(self):
        self.menu.audio_available = False
        self.menu.toggle_music()
        self.menu.set_volume(.5)
        self.menu.draw()
        self.menu.open_modal('selector')
        with patch('main.subprocess.Popen', side_effect=OSError):
            self.menu.launch_game()
        self.assertIsNone(self.menu.child)
        self.assertTrue(self.menu.notice)

    def test_text_stays_inside_canvas_and_dialog(self):
        original = self.menu.text
        def checked(value, pos, *args, **kwargs):
            rect = original(value, pos, *args, **kwargs)
            self.assertTrue(self.menu.canvas.get_rect().contains(rect), value)
            if self.menu.modal and pos[0] >= 308 and 194 <= pos[1] <= 600:
                self.assertTrue(pygame.Rect(260, 170, 760, 460).contains(rect), value)
            return rect
        with patch.object(self.menu, 'text', side_effect=checked):
            self.menu.draw()
            for modal in ('selector', 'load', 'lab', 'quit'):
                self.menu.open_modal(modal)
                self.menu.draw_modal()
