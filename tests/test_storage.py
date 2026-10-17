import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from engine.game.storage import Profile


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.profile = Profile(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_profile_roundtrip(self):
        self.profile.highscores['expert'] = 15000
        self.profile.settings['volume'] = .3
        self.profile.achievements.add('boss')
        self.profile.saved_game = {'version': 1, 'score': 500}
        self.assertTrue(self.profile.write())
        reopened = Profile(self.directory.name)
        self.assertEqual(reopened.highscores['expert'], 15000)
        self.assertEqual(reopened.settings['volume'], .3)
        self.assertEqual(reopened.achievements, {'boss'})
        self.assertEqual(reopened.saved_game, self.profile.saved_game)

    def test_corrupt_and_oversized_profile_recover(self):
        self.profile.path.write_text('{broken', encoding='utf-8')
        reopened = Profile(self.directory.name)
        self.assertTrue(reopened.error)
        self.assertIsNone(reopened.saved_game)
        self.profile.path.write_bytes(b' ' * 2_000_001)
        self.assertTrue(Profile(self.directory.name).error)

    def test_failed_atomic_write_preserves_previous_profile(self):
        self.assertTrue(self.profile.write())
        before = self.profile.path.read_bytes()
        self.profile.highscores['normal'] = 123
        with patch.object(Path, 'replace', side_effect=OSError('read only')):
            self.assertFalse(self.profile.write())
        self.assertEqual(self.profile.path.read_bytes(), before)
        self.assertEqual(list(Path(self.directory.name).glob('*.tmp')), [])

    def test_invalid_metadata_cannot_override_defaults(self):
        data = {'version': 1, 'settings': {'volume': float('nan'), 'effects': 'yes'},
                'highscores': {'normal': -5}, 'achievements': ['boss', {}, 'unknown']}
        self.profile.path.write_text(json.dumps(data))
        reopened = Profile(self.directory.name)
        self.assertEqual(reopened.settings['volume'], .6)
        self.assertTrue(reopened.settings['effects'])
        self.assertEqual(reopened.highscores['normal'], 0)
        self.assertEqual(reopened.achievements, {'boss'})
