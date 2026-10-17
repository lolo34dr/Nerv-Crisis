import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import pygame
from main import Menu
from engine.game.assets import ResourceLoader


class ResourceLoaderTests(unittest.TestCase):
    def test_only_completed_operations_advance_progress(self):
        completed = []
        loader = ResourceLoader([('first', lambda: completed.append(1)),
                                 ('second', lambda: completed.append(2))])
        self.assertFalse(loader.ready)
        self.assertEqual(loader.progress, 0)
        loader.step()
        self.assertEqual(completed, [1])
        self.assertEqual(loader.progress, .5)
        self.assertFalse(loader.ready)
        loader.step()
        self.assertEqual(completed, [1, 2])
        self.assertTrue(loader.ready)
        self.assertEqual(loader.progress, 1)

    def test_failed_resource_does_not_advance_until_successful_retry(self):
        attempts = []
        def work():
            attempts.append(1)
            if len(attempts) == 1:
                raise OSError('missing resource')
        loader = ResourceLoader([('artwork', work)])
        loader.step()
        self.assertFalse(loader.ready)
        self.assertEqual(loader.progress, 0)
        self.assertTrue(loader.error)
        loader.step()
        self.assertEqual(len(attempts), 1)
        loader.retry()
        loader.step()
        self.assertTrue(loader.ready)


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()

    def tearDown(self):
        pygame.quit()
        self.directory.cleanup()

    def test_default_fullscreen_black_splash_then_actual_resource_loading(self):
        menu = Menu(data_directory=self.directory.name)
        self.assertTrue(menu.fullscreen)
        self.assertTrue(menu.window.get_flags() & pygame.FULLSCREEN)
        menu.intro_elapsed = .9
        menu.draw()
        self.assertEqual(menu.canvas.get_at((0, 0))[:3], (0, 0, 0))
        self.assertGreater(pygame.surfarray.array3d(menu.canvas).max(), 0)
        self.assertFalse(menu.loader.ready)
        self.assertIsNone(menu.combat_assets)
        menu.update(2)
        self.assertFalse(menu.intro)
        self.assertEqual(menu.loader.completed, 0)
        # A huge timestep still runs just one operation, rather than filling a timed bar.
        menu.update(500)
        self.assertEqual(menu.loader.completed, 1)
        self.assertIsNotNone(menu.profile)
        self.assertIsNone(menu.combat_assets)
        for _ in range(len(menu.loader.jobs) - 1):
            menu.draw()
            menu.present()
            menu.update(.01)
        self.assertTrue(menu.loader.ready)
        self.assertIsNotNone(menu.combat_assets)
        menu.draw()
        menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11))
        self.assertFalse(menu.fullscreen)
        menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11))
        self.assertTrue(menu.fullscreen)

    def test_splash_skip_cannot_skip_loading_or_launch_unprepared_game(self):
        menu = Menu(data_directory=self.directory.name, fullscreen=False)
        menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertFalse(menu.intro)
        self.assertFalse(menu.loader.ready)
        menu.launch_game()
        self.assertIsNone(menu.game)
        menu.update(.01)
        self.assertEqual(menu.loader.completed, 1)

    def test_game_reuses_loaded_art_and_fonts(self):
        menu = Menu(skip_intro=True, data_directory=self.directory.name, fullscreen=False)
        with patch('pygame.image.load') as image, patch('pygame.font.Font') as font:
            menu.launch_game()
            self.assertIs(menu.game.assets, menu.combat_assets)
            self.assertIs(menu.game.art, menu.combat_assets.art)
        image.assert_not_called()
        font.assert_not_called()

    def test_loading_error_is_visible_and_retryable(self):
        menu = Menu(data_directory=self.directory.name, fullscreen=False)
        menu.intro = False
        original = menu.loader.jobs[0]
        def fail():
            raise OSError('profile temporarily unavailable')
        menu.loader.jobs[0] = ('Read pilot profile', fail)
        menu.update(.1)
        self.assertEqual(menu.loader.completed, 0)
        self.assertTrue(menu.loader.error)
        menu.draw()
        menu.loader.jobs[0] = original
        menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
        menu.update(.1)
        self.assertEqual(menu.loader.completed, 1)
        menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertFalse(menu.running)

    def test_missing_audio_does_not_block_gameplay(self):
        with patch('pygame.mixer.init', side_effect=pygame.error('No device')):
            menu = Menu(skip_intro=True, data_directory=self.directory.name, fullscreen=False)
        self.assertTrue(menu.loader.ready)
        self.assertFalse(menu.audio_available)
        menu.launch_game()
        self.assertIsNotNone(menu.game)
