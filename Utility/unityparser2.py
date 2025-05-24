import itertools
import math
import os
import re
from dataclasses import dataclass
from io import StringIO
from itertools import starmap
from pathlib import Path
from typing import TextIO, Self, Callable

import yaml
from yaml import Node, MappingNode, Loader
from yaml.composer import Composer
from yaml.constructor import SafeConstructor
from yaml.parser import Parser
from yaml.reader import Reader
from yaml.resolver import Resolver
from yaml.scanner import Scanner

from Utility.multirun import run_multiprocess
from Utility.timer import Timeit


def unity_load_yaml(text_io: TextIO, try_preserve_types=False):
    """
    :param text_io: Text wrapper of text to parse
    :param try_preserve_types: If true, will deserialize what seems to be int and float types to the same Python
        data types instead of deserializing them all as the string type. When/if this value is later serialized
        back it might be represented differently in some corner cases.
    """
    from unityparser.loader import SmartUnityLoader
    from unityparser.register import UnityScalarRegister
    from unityparser.utils import load_all
    from unityparser import UnityDocument
    from unityparser.loader import UnityLoader
    from unityparser.utils import UNIX_LINE_ENDINGS

    loader_cls = SmartUnityLoader if try_preserve_types else UnityLoader
    register = UnityScalarRegister()
    with text_io as fp:
        loader = loader_cls(fp)
        loader.check_data()
        fp.seek(0)
        version = loader.yaml_version
        tags = loader.non_default_tags
        data = [d for d in load_all(fp, register, loader_cls)]
        # use document line endings if no mixed lien endings found, else default to linux
        line_endings = UNIX_LINE_ENDINGS if isinstance(fp.newlines, tuple) else fp.newlines
    doc = UnityDocument(data, newline=line_endings, file_path=None, register=register, version=version,
                        tags=tags)
    return doc

@dataclass
class UnityDoc:
    entries: list["UnityYAMLEntry"]

    @staticmethod
    def yaml_parse_text_smart(text: str) -> Self:
        if len(text) < 1e6:
            return UnityDoc.yaml_parse_text(text)
        else:
            return UnityDoc.yaml_parse_text_parallel(text)

    @staticmethod
    def yaml_parse_io_smart(text_io: TextIO) -> Self:
        with text_io as _f:
            text = _f.read()
        return UnityDoc.yaml_parse_text_smart(text)

    @staticmethod
    def yaml_parse_file_smart(path: os.PathLike[str]) -> Self:
        with open(path, "r", encoding="UTF-8") as _f:
            return UnityDoc.yaml_parse_io_smart(_f)

    @staticmethod
    def yaml_parse_text(text: str) -> Self:
        entries = list(yaml.load_all(text, UnityLoaderR))
        return UnityDoc(entries)

    @staticmethod
    def yaml_parse_io(text_io: TextIO) -> Self:
        with text_io as _f:
            text = _f.read()
        return UnityDoc.yaml_parse_text(text)

    @staticmethod
    def yaml_parse_file(path: os.PathLike[str]) -> Self:
        with open(path, "r", encoding="UTF-8") as _f:
            return UnityDoc.yaml_parse_io(_f)

    @staticmethod
    def yaml_parse_text_parallel(text: str, filter_func: Callable[[str], bool] = None) -> Self:
        unity_tag = "--- "
        text_split = text.split(unity_tag)[1:]

        if filter_func:
            text_split = filter(filter_func, text_split)

        text_split_enum: enumerate[str] = enumerate(map(lambda x: unity_tag + x, text_split))

        text_split_parts_list = starmap(_split_yaml_string, text_split_enum)
        text_split_parts = (part for parts in text_split_parts_list for part in parts) # flatten

        entries_parts = run_multiprocess(_yaml_load_part, text_split_parts)

        entries: list[UnityYAMLEntry | None] = [None] * (entries_parts[-1][0] + 1)
        for entry_index, part_index, entry in entries_parts:
            if not entries[entry_index]:
                entries[entry_index] = entry
            else:
                entries[entry_index].extend_data(entry)

        return UnityDoc(entries)

    @staticmethod
    def yaml_parse_io_parallel(text_io: TextIO, filter_func: Callable[[str], bool] = None) -> Self:
        with text_io as _f:
            text = _f.read()
        return UnityDoc.yaml_parse_text_parallel(text, filter_func)

    @staticmethod
    def yaml_parse_file_parallel(path: os.PathLike[str], filter_func: Callable[[str], bool] = None) -> Self:
        with open(path, "r", encoding="UTF-8") as _f:
            return UnityDoc.yaml_parse_io_parallel(_f, filter_func)


def _yaml_load_part(i: int, j: int, entry: str) -> tuple[int, int, "UnityYAMLEntry"]:
    return i, j, yaml.load(entry, UnityLoaderR)


MAX_PARSE_BATCH_SIZE = 1 << 12
def _split_yaml_string(entry_index: int, entry: str) -> list[tuple[int, int, str]]:
    """
    Assumption: Only long part is dictionary in form of " - first: ... second: ... " (m_Tiles)
    """

    FIRST = "- first"

    if FIRST not in entry:
        return [(entry_index, 0, entry)]

    header: str = ""
    dictionary: list[str] = []
    footer: str = ""

    dict_entry = ""
    dict_indent = 0
    parse_stage = 0
    with StringIO(entry) as string:
        for line in string.readlines():
            match parse_stage:
                case 0:
                    if FIRST in line:
                        dict_indent = re.search(r"\S", line).start()
                        parse_stage = 1
                        dict_entry += line
                        continue
                    header += line

                case 1:
                    if FIRST in line:
                        if dict_entry:
                            dictionary.append(dict_entry)
                            dict_entry = ""
                    elif re.search(r"\S", line).start() == dict_indent:
                        parse_stage = 2
                        footer += line
                        dictionary.append(dict_entry)
                        continue

                    dict_entry += line

                case 2:
                    footer += line

    # check = header + "".join(dictionary) + footer
    # assert entry == check

    ret = []
    for part_index, batch in enumerate(itertools.batched(dictionary, MAX_PARSE_BATCH_SIZE)):
        data = header + "".join(batch) + footer
        ret.append((entry_index, part_index, data))

    return ret

@dataclass
class UnityYAMLEntry:
    className: str
    classID: int
    fileID: int
    data: dict

    def __repr__(self):
        return f"<{self.__class__.__name__} className={self.className}, fileID={self.fileID}>"

    def extend_data(self, other: Self):
        assert self.fileID == other.fileID
        self.data["m_Tiles"].extend(other.data["m_Tiles"])


class UnityParserR(Parser):
    DEFAULT_TAGS = {u"!u!": u"tag:unity3d.com,2011"}
    DEFAULT_TAGS.update(Parser.DEFAULT_TAGS)


class UnityLoaderR(Reader, Scanner, UnityParserR, Composer, SafeConstructor, Resolver):
    def __init__(self, stream):
        yaml.add_multi_constructor('tag:unity3d.com,2011', self.unity_yaml_constructor, UnityLoaderR)

        Reader.__init__(self, stream)
        Scanner.__init__(self)
        UnityParserR.__init__(self)
        Composer.__init__(self)
        SafeConstructor.__init__(self)
        Resolver.__init__(self)

    @staticmethod
    def unity_yaml_constructor(loader: Loader, suffix: str, node: MappingNode | Node):
        snippet = node.start_mark.get_snippet().replace("--- !u!", "").replace("^", "")
        class_id, file_id = map(int, snippet.strip().split("&"))

        yaml_object: dict = loader.construct_mapping(node)
        class_name, data = list(yaml_object.items())[0]
        assert len(yaml_object.keys()) == 1, "For each tag (!u!) there must by only one entry"

        return UnityYAMLEntry(class_name, class_id, file_id, data)


if __name__ == "__main__":
    # fp = r"C:\Programs\GitHub\VampireSurvivorsFiles_RAW_no_git\0VS\ExportedProject\Assets\GameObject\AstralStair.prefab"
    # fp = r"C:\Programs\GitHub\VampireSurvivorsFiles_RAW_no_git\0VS\ExportedProject\Assets\GameObject\CarloCart.prefab"
    # fp = r"C:\Programs\GitHub\VampireSurvivorsFiles_RAW_no_git\0VS\ExportedProject\Assets\GameObject\Coop.prefab"
    fp = r"C:\Programs\GitHub\VampireSurvivorsFiles\Images\Generated\_Tilemaps\__Test\Coop_t.prefab"

    fp = Path(fp)


    def __timeit():
        from unityparser import UnityDocument

        timeit = Timeit()
        par = UnityDoc.yaml_parse_file_parallel(fp)
        print(timeit)

        timeit = Timeit()
        seq1 = UnityDoc.yaml_parse_file_smart(fp)
        print(timeit)

        timeit = Timeit()
        seq = UnityDoc.yaml_parse_file(fp)
        print(timeit)


        # timeit = Timeit()
        # UnityDocument.load_yaml(fp)
        # print(timeit)

        assert par == seq

    # __timeit()


    def __profile():
        from Images.tilemap_gen import __load_UnityDocument
        import cProfile
        print("Started")
        with cProfile.Profile() as pr:
            UnityDoc.yaml_parse_file_parallel(fp, lambda x: "Tilemap:" in x)
            pr.print_stats('time')

        print("Started")
        with cProfile.Profile() as pr:
            __load_UnityDocument(fp)
            pr.print_stats('time')


    __profile()

    pass
