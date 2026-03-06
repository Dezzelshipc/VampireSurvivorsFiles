import asyncio

from req_test import check_pydub_defer
from Source.Utility.special_classes import Objectless


class DeferConstants(Objectless):
    _pydub_defer_checker = check_pydub_defer()
    _is_pydub = None

    @classmethod
    def is_pydub(cls) -> bool:
        if cls._is_pydub is None:
            cls._is_pydub = asyncio.run(cls._pydub_defer_checker)
        return cls._is_pydub
