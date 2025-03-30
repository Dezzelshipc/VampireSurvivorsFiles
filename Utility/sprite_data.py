from dataclasses import dataclass
from tkinter import Image

from typing import TypeVar, Iterator

TRect = TypeVar("TRect", bound="SpriteRect")
TPivot = TypeVar("TPivot", bound="SpritePivot")


@dataclass
class SpriteRect:
    x: float
    y: float
    width: float
    height: float

    @staticmethod
    def from_dict(args: dict[str, float]) -> TRect:
        return SpriteRect(args["x"], args["y"], args["width"], args["height"])

    def __getitem__(self, item):
        # SHOULD NOT BE USED NORMALLY
        return self.__getattribute__(item)


@dataclass
class SpritePivot:
    x: float
    y: float

    @staticmethod
    def from_dict(args: dict[str, float]) -> TPivot:
        return SpritePivot(args["x"], args["y"])

    def __getitem__(self, item):
        # SHOULD NOT BE USED NORMALLY
        return self.__getattribute__(item)


class AnimationData:
    def __init__(self, name: str, frames_names: list[str], rects: list[SpriteRect], sprites: list[Image]):
        self.name = name
        self._frames_names = frames_names
        self._rects = rects
        self._sprites = sprites

    def get_sprites_iter(self) -> Iterator[tuple[Image, SpriteRect, str]]:
        return zip(self._sprites, self._rects, self._frames_names)

    def __len__(self):
        return len(self._frames_names)


class SpriteData:
    def __init__(self, name: str, real_name: str, internal_id_set: set[int], rect: SpriteRect | dict[str, float],
                 pivot: SpritePivot | dict[str, float]):
        self.name = name
        self.real_name = real_name
        self.internal_id_set = internal_id_set
        self.rect = rect if isinstance(rect, SpriteRect) else SpriteRect.from_dict(rect)
        self.pivot = pivot if isinstance(pivot, SpritePivot) else SpritePivot.from_dict(pivot)

        self.sprite: Image | None = None
        self.animation: AnimationData | None = None

    def __repr__(self):
        return super().__repr__().replace(" object", f": {self.real_name}, {self.sprite=}")

    def __getitem__(self, item):
        # SHOULD NOT BE USED NORMALLY
        return self.__getattribute__(item)


SKIP_ANIM_NAMES_LIST = [
    "random_00", "random_99"
]
