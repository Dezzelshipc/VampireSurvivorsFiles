import asyncio
import sys
from pathlib import Path

from Utility.req_test import check_pydub_defer
from Utility.singleton import Singleton

IS_DEBUG: bool = (sys.monitoring.get_tool(sys.monitoring.DEBUGGER_ID)) is not None or (sys.gettrace() is not None)

ROOT_FOLDER = Path(__file__).parent.parent.absolute()

AUDIO_FOLDER = ROOT_FOLDER / "Audio"
CONFIG_FOLDER = ROOT_FOLDER / "Config"
DATA_FOLDER = ROOT_FOLDER / "Data"
IMAGES_FOLDER = ROOT_FOLDER / "Images"
RIPPER_FOLDER = ROOT_FOLDER / "Ripper"
TRANSLATIONS_FOLDER = ROOT_FOLDER / "Translations"
UTILITY_FOLDER = ROOT_FOLDER / "Utility"

GENERATED = "Generated"
TILEMAPS = "_Tilemaps"

RESOURCES = "Resources"
TEXTURE_2D = "Texture2D"
TEXT_ASSET = "TextAsset"
GAME_OBJECT = "GameObject"
PREFAB_INSTANCE = "PrefabInstance"
AUDIO_CLIP = "AudioClip"
MONO_BEHAVIOUR = "MonoBehaviour"

DATA_MANAGER_SETTINGS = "DataManagerSettings"
BUNDLE_MANIFEST_DATA = "BundleManifestData"


class DeferConstants(metaclass=Singleton):
    _pydub_defer_checker = check_pydub_defer()
    _is_pydub = None

    @classmethod
    def is_pydub(cls) -> bool:
        if cls._is_pydub is None:
            cls._is_pydub = asyncio.run(cls._pydub_defer_checker)
        return cls._is_pydub


DEFAULT_ANIMATION_FRAME_RATE = 7
