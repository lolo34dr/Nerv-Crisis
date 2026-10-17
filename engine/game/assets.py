"""Main-thread resource loading and reusable combat assets."""
from dataclasses import dataclass

import pygame

from .variable import ASSETS, pixel_font


class ResourceLoader:
    """A completed operation advances progress; elapsed time never does."""
    def __init__(self, jobs):
        self.jobs = jobs
        self.completed = 0
        self.error = ''

    @property
    def ready(self):
        return self.completed == len(self.jobs)

    @property
    def progress(self):
        return self.completed / len(self.jobs) if self.jobs else 1.0

    @property
    def label(self):
        return 'All resources ready' if self.ready else self.jobs[self.completed][0]

    def step(self):
        if self.ready or self.error:
            return
        try:
            self.jobs[self.completed][1]()
        except (pygame.error, OSError, ValueError) as error:
            self.error = f'{self.label}: {error}'
            return
        self.completed += 1

    def retry(self):
        self.error = ''


@dataclass
class CombatAssets:
    font: pygame.font.Font
    small: pygame.font.Font
    title: pygame.font.Font
    art: pygame.Surface

    @classmethod
    def load(cls, image=None, title=None):
        if image is None:
            image = pygame.image.load(str(ASSETS / 'images/evangelion.png')).convert_alpha()
        return cls(pygame.font.Font(None, 26), pygame.font.Font(None, 22),
                   title or pygame.font.Font(pixel_font, 32),
                   pygame.transform.smoothscale(image, (232, 232)))
