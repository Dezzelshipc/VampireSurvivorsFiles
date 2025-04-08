import sys
from abc import ABC
from typing import TextIO

from Utility.constants import ROOT_FOLDER
from Utility.utility import clear_file


class Logger(TextIO, ABC):

    log_path = ROOT_FOLDER / "unpacker.log"

    def __init__(self, stream):
        self.stream = stream
        clear_file(self.log_path)

    def log(self):
        return open(self.log_path, "a")

    def write(self, __s):
        self.stream.write(__s)
        if "\r" not in __s:
            with self.log() as l:
                l.write(__s)

    def flush(self):
        self.stream.flush()
        with self.log() as l:
            l.flush()
