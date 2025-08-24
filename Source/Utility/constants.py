import asyncio
import sys
from pathlib import Path
from typing import Final, Callable

from Source.Utility.req_test import check_pydub_defer
from Source.Utility.special_classes import Objectless
from Source.Utility.utility import _find_main_py_file

IS_DEBUG: Final[bool] = (sys.monitoring.get_tool(sys.monitoring.DEBUGGER_ID)) is not None or (
        sys.gettrace() is not None)

ROOT_FOLDER: Final[Path] = _find_main_py_file().parent.absolute()

AUDIO_FOLDER: Final[Path] = ROOT_FOLDER / "Audio"
CONFIG_FOLDER: Final[Path] = ROOT_FOLDER / "Config"
DATA_FOLDER: Final[Path] = ROOT_FOLDER / "Data"
IMAGES_FOLDER: Final[Path] = ROOT_FOLDER / "Images"
RIPPER_FOLDER: Final[Path] = ROOT_FOLDER / "Ripper"
TRANSLATIONS_FOLDER: Final[Path] = ROOT_FOLDER / "Translations"
UTILITY_FOLDER: Final[Path] = ROOT_FOLDER / "Utility"

SOURCE: Final[str] = "Source"
GENERATED: Final[str] = "Generated"
SPLIT: Final[str] = "Split"
TILEMAPS: Final[str] = "_Tilemaps"

RESOURCES: Final[str] = "Resources"
TEXTURE_2D: Final[str] = "Texture2D"
TEXT_ASSET: Final[str] = "TextAsset"
GAME_OBJECT: Final[str] = "GameObject"
PREFAB_INSTANCE: Final[str] = "PrefabInstance"
AUDIO_CLIP: Final[str] = "AudioClip"
MONO_BEHAVIOUR: Final[str] = "MonoBehaviour"

DATA_MANAGER_SETTINGS: Final[str] = "DataManagerSettings"
BUNDLE_MANIFEST_DATA: Final[str] = "BundleManifestData"


class COMPOUND_DATA(Objectless):
    """
    Special constant class for representing aggregated data from every DLC.
    Uses type 'COMPOUND_DATA_TYPE'.
    Cannot be instantiated directly. Should be used as 'COMPOUND_DATA'
    """
    value = "Compound Data"

    @classmethod
    def __repr__(cls) -> str:
        return f"{cls.value} (all DLC)"


COMPOUND_DATA_TYPE = COMPOUND_DATA.__class__

PROGRESS_BAR_FUNC_TYPE = Callable[[int | float, int | float], None]


def to_source_path(path: Path) -> Path:
    start = path.parent
    end = path.name
    return start / SOURCE / end


class DeferConstants(Objectless):
    _pydub_defer_checker = check_pydub_defer()
    _is_pydub = None

    @classmethod
    def is_pydub(cls) -> bool:
        if cls._is_pydub is None:
            cls._is_pydub = asyncio.run(cls._pydub_defer_checker)
        return cls._is_pydub


DEFAULT_ANIMATION_FRAME_RATE: Final[int] = 7
