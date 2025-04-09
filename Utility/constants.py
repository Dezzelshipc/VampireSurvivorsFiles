import asyncio
import sys
from pathlib import Path

from Utility.req_test import check_pydub_defer
from Utility.singleton import Singleton

IS_DEBUG: bool = (sys.monitoring.get_tool(sys.monitoring.DEBUGGER_ID)) is not None or (sys.gettrace() is not None)

ROOT_FOLDER = Path(__file__).parent.parent.absolute()

class DeferConstants(metaclass=Singleton):
    _pydub_defer_checker = check_pydub_defer()
    _is_pydub = None

    @classmethod
    def is_pydub(cls) -> bool:
        if cls._is_pydub is None:
            cls._is_pydub = asyncio.run(cls._pydub_defer_checker)
        return cls._is_pydub