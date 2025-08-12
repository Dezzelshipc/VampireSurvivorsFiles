from io import StringIO
from typing import TextIO

from Utility.constants import ROOT_FOLDER
from Utility.utility import clear_file


class Logger(StringIO):
    log_path = ROOT_FOLDER / "unpacker.log"

    def __init__(self, stream: TextIO):
        super().__init__()
        self.stream = stream
        clear_file(self.log_path)

    def log(self):
        return open(self.log_path, "a", encoding="UTF-8")

    def write(self, __s):
        self.stream.write(__s)
        if "\r" not in __s:
            with self.log() as l:
                l.write(__s)

    def flush(self):
        self.stream.flush()
        with self.log() as l:
            l.flush()
