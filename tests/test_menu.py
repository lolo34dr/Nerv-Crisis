"""Exercise real menu state transitions, rendering, and resized mouse coordinates."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
import pygame
from main import Menu, SIZE


class MenuTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.menu = Menu(skip_intro=True, data_directory=self.directory.name, fullscreen=False)

    def tearDown(self):
        pygame.quit()
        self.directory.cleanup()

    def key(self, value):
        self.menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=value))

    def click(self, position):
        viewport = self.menu.viewport()
        position = (viewport.x + round(position[0] * viewport.w / SIZE[0]),
                    viewport.y + round(position[1] * viewport.h / SIZE[1]))
        self.menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=position, button=1))

    def test_keyboard_launch_uses_same_window_and_audio(self):
        display = self.menu.window
        with patch('pygame.display.set_mode') as window, patch('subprocess.Popen') as process, \
                patch('pygame.mixer.music.load') as load, patch('pygame.mixer.music.pause') as pause:
            self.key(pygame.K_RETURN)
            self.assertEqual(self.menu.modal, 'selector')
            self.key(pygame.K_RETURN)
            self.assertIs(self.menu.game.screen, self.menu.canvas)
            self.assertIs(self.menu.window, display)
            self.assertEqual(self.menu.game.state, 'playing')
            self.menu.draw()
            self.menu.present()
        window.assert_not_called()
        process.assert_not_called()
        load.assert_not_called()
        pause.assert_not_called()

    def test_pause_settings_return_and_new_session_save_load(self):
        self.menu.launch_game()
        self.menu.game.score = 1250
        self.key(pygame.K_p)
        self.assertEqual(self.menu.game.state, 'paused')
        self.key(pygame.K_DOWN)
        self.key(pygame.K_RETURN)
        self.assertEqual(self.menu.modal, 'lab')
        elapsed = self.menu.game.elapsed
        self.menu.update(.05)
        self.assertEqual(self.menu.game.elapsed, elapsed)
        self.key(pygame.K_ESCAPE)
        self.assertEqual(self.menu.game.state, 'paused')
        self.key(pygame.K_DOWN)  # Save and menu.
        self.key(pygame.K_RETURN)
        self.assertIsNone(self.menu.game)
        self.assertEqual(self.menu.profile.highscores['normal'], 1250)
        reopened = Menu(skip_intro=True, data_directory=self.directory.name, fullscreen=False)
        reopened.activate(1)
        reopened.modal_action(0)
        self.assertEqual(reopened.game.score, 1250)
        self.assertEqual(reopened.game.state, 'paused')
        reopened.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(reopened.game.state, 'playing')

    def test_record_before_replay_and_return_menu(self):
        self.menu.launch_game()
        self.menu.game.score = 6000
        self.menu.game.kills = 30
        self.menu.game.bosses_defeated = 1
        self.menu.game.state = 'gameover'
        self.key(pygame.K_RETURN)
        self.assertEqual(self.menu.profile.highscores['normal'], 6000)
        self.assertIn('boss', self.menu.profile.achievements)
        self.assertEqual(self.menu.game.score, 0)
        self.key(pygame.K_p)
        for _ in range(3):
            self.key(pygame.K_DOWN)
        self.key(pygame.K_RETURN)
        self.assertIsNone(self.menu.game)

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
        for modal in ('selector', 'lab', 'load', 'quit', 'records', 'help'):
            self.menu.open_modal(modal)
            self.menu.draw()
            self.menu.present()
        self.menu.handle_event(pygame.event.Event(pygame.QUIT))
        self.assertFalse(self.menu.running)

    def test_no_audio_and_invalid_saved_game(self):
        self.menu.audio_available = False
        self.menu.toggle_music()
        self.menu.set_volume(.5)
        self.menu.draw()
        self.menu.profile.saved_game = {'version': 999}
        self.menu.launch_game(resume=True)
        self.assertIsNone(self.menu.game)
        self.assertTrue(self.menu.notice)

    def test_difficulty_settings_and_effects_persist(self):
        self.menu.open_modal('selector')
        self.key(pygame.K_RIGHT)
        self.assertEqual(self.menu.difficulty, 'expert')
        self.key(pygame.K_ESCAPE)
        self.menu.open_modal('lab')
        self.key(pygame.K_v)
        self.assertFalse(self.menu.effects)
        self.key(pygame.K_ESCAPE)
        reopened = Menu(skip_intro=True, data_directory=self.directory.name, fullscreen=False)
        self.assertEqual(reopened.difficulty, 'expert')
        self.assertFalse(reopened.effects)

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
            for modal in ('selector', 'load', 'lab', 'quit', 'records', 'help'):
                self.menu.open_modal(modal)
                self.menu.draw_modal()

    def test_help_pauses_mission_and_closes_without_resuming(self):
        self.menu.launch_game()
        self.key(pygame.K_h)
        self.assertEqual(self.menu.modal, 'help')
        self.assertEqual(self.menu.game.state, 'paused')
        elapsed = self.menu.game.elapsed
        self.menu.update(.1)
        self.assertEqual(self.menu.game.elapsed, elapsed)
        self.key(pygame.K_RETURN)
        self.assertIsNone(self.menu.modal)
        self.assertEqual(self.menu.game.state, 'paused')
        self.key(pygame.K_p)
        self.assertEqual(self.menu.game.state, 'playing')
