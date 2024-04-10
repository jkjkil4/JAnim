
from typing import Self

from janim.components.audio_data import Cmpt_AudioWav
from janim.components.component import CmptInfo
from janim.items.item import Item


class Audio(Item):
    wav = CmptInfo(Cmpt_AudioWav[Self])

    def __init__(self, filepath: str, begin: float = -1, end: float = -1, **kwargs):
        super().__init__(**kwargs)
        self.wav.read(filepath, begin, end)
