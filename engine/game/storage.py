"""Local JSON profile. No game data is written to the repository."""
import json
import math
import os
from pathlib import Path
import tempfile

DIFFICULTIES = {'cadet': .75, 'normal': 1.0, 'expert': 1.35}
ACHIEVEMENTS = {'first_blood': 'First contact', 'hunter': 'Hunter: 25 enemies',
                'boss': 'Angel defeated', 'survivor': 'Wave 5 reached',
                'score': 'Score 5,000 points', 'objectives': 'Complete 3 wave objectives'}


def data_directory():
    if os.environ.get('NERV_DATA_DIR'):
        return Path(os.environ['NERV_DATA_DIR']).expanduser()
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'Nerv-Crisis'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'Nerv-Crisis'


class Profile:
    def __init__(self, directory=None):
        self.path = (Path(directory) if directory is not None else data_directory()) / 'profile.json'
        self.error = ''
        self.settings = {'volume': .6, 'music_paused': False, 'effects': True, 'difficulty': 'normal'}
        self.highscores = dict.fromkeys(DIFFICULTIES, 0)
        self.achievements = set()
        self.saved_game = None
        try:
            if not self.path.exists():
                return
            if self.path.stat().st_size > 2_000_000:
                raise ValueError('profile too large')
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data, dict) or data.get('version') != 1:
                raise ValueError('unknown profile version')
            settings = data.get('settings', {})
            if not isinstance(settings, dict):
                raise ValueError('invalid settings')
            volume = settings.get('volume', .6)
            if type(volume) in (float, int) and math.isfinite(volume):
                self.settings['volume'] = max(0, min(1, volume))
            for key in ('music_paused', 'effects'):
                if type(settings.get(key)) is bool:
                    self.settings[key] = settings[key]
            if settings.get('difficulty') in DIFFICULTIES:
                self.settings['difficulty'] = settings['difficulty']
            scores = data.get('highscores', {})
            if isinstance(scores, dict):
                for key in DIFFICULTIES:
                    if type(scores.get(key)) is int and 0 <= scores[key] <= 1_000_000_000:
                        self.highscores[key] = scores[key]
            badges = data.get('achievements', [])
            if isinstance(badges, list):
                self.achievements = {key for key in badges if isinstance(key, str) and key in ACHIEVEMENTS}
            if isinstance(data.get('saved_game'), dict):
                self.saved_game = data['saved_game']
        except (OSError, ValueError, TypeError):
            self.error = 'Profile unreadable: using default settings.'

    def write(self):
        """Replace atomically so an interrupted write preserves the previous profile."""
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             prefix='.profile-', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                json.dump({'version': 1, 'settings': self.settings, 'highscores': self.highscores,
                           'achievements': sorted(self.achievements), 'saved_game': self.saved_game},
                          stream, ensure_ascii=False, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.path)
            self.error = ''
            return True
        except (OSError, ValueError, TypeError):
            self.error = 'Cannot write save data. Check your save folder permissions.'
            return False
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def record(self, game):
        self.highscores[game.difficulty] = max(self.highscores[game.difficulty], game.score)
        if game.kills:
            self.achievements.add('first_blood')
        if game.kills >= 25:
            self.achievements.add('hunter')
        if game.bosses_defeated:
            self.achievements.add('boss')
        if game.wave >= 5:
            self.achievements.add('survivor')
        if game.score >= 5000:
            self.achievements.add('score')
        if game.objectives_completed >= 3:
            self.achievements.add('objectives')
        return self.write()
