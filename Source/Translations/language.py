import json
from collections import OrderedDict
from enum import Enum
from typing import Final, Any

from Source.Utility.constants import COMPOUND_DATA
from Source.Utility.constants import COMPOUND_DATA_TYPE
from Source.Utility.meta_data import MetaDataHandler
from Source.Utility.special_classes import Objectless
from Source.Utility.unityparser2 import UnityDoc
from Source.Utility.timer import Timeit

I2_LANGUAGES: Final[str] = "I2Languages"


class LangType(Enum):
    ACHIEVEMENT = "achievementLang"
    ADVENTURE = "adventureLang"
    ARCANA = "arcanaLang"
    CHARACTER = "characterLang"
    ENEMIES = "enemiesLang"
    EVENT = "eventLang"
    GLOSSARY = "Glossary"
    ITEM = "itemLang"
    GENERAL = "lang"
    MUSIC = "musicLang"
    POWER_UP = "powerUpLang"
    PROGRESS = "progressLang"
    SECRET = "secretLang"
    SKIN = "skinLang"
    STAGE = "stageLang"
    WEAPON = "weaponLang"
    XBOX_ACH = "Xbox Achievements"

    NONE = None

    @classmethod
    def get_all_types(cls) -> set["LangType"]:
        return {*cls}.difference({cls.NONE})


class Lang(Enum):
    EN = "en"
    FR = "fr"
    IT = "it"
    DE = "de"
    ES = "es"
    PT_BR = "pt-BR"
    PL = "pl"
    RU = "ru"
    TR = "tr"
    ZH_CN = "zh-CN"
    JS = "ja"
    KO = "ko"
    ZH_TW = "zh-TW"
    UK = "uk"

    @classmethod
    def get_all_langs(cls) -> set["Lang"]:
        return {*cls}


class LangFile:
    __lang_type: LangType | COMPOUND_DATA_TYPE
    __data: OrderedDict[str, Any] | None = None
    __lang_data: OrderedDict[Lang, dict[str, Any]] | None = None
    __raw_text: str | None = None
    __json_text: str | None = None

    def __init__(self, lang_type: LangType | COMPOUND_DATA_TYPE, data: dict[str, Any] | None = None,
                 raw_text: str | None = None):
        self.__lang_type = lang_type
        if data:
            self.__data = data
        elif raw_text:
            # Raw text in yaml
            self.__raw_text = raw_text

    def __load(self):
        if self.__data and not self.__raw_text:
            self.__raw_text = self.__json_text = json.dumps(self.__data, ensure_ascii=False, indent=2)
        elif self.__raw_text and not self.__data:
            self.__data = UnityDoc.yaml_parse_text_smart(self.__raw_text).entries[0].data
            self.__json_text = json.dumps(self.__data, ensure_ascii=False, indent=2)

    def __load_inverse(self):
        self.__load()
        if not self.__lang_data:
            self.__lang_data = gen_inverse_dict(self.__lang_type)

    def data(self) -> dict[str, Any]:
        self.__load()
        return self.__data

    def raw_text(self) -> str:
        self.__load()
        return self.__raw_text

    def json_text(self) -> str:
        self.__load()
        return self.__json_text

    def lang_data(self) -> dict[Lang, dict[str, Any]]:
        assert self.__lang_type != COMPOUND_DATA
        self.__load_inverse()
        return self.__lang_data

    def get_lang(self, lang: Lang) -> dict[str, Any]:
        return self.lang_data()[lang]


class LangHandler(Objectless):
    _full_file: LangFile = None
    _loaded_data: dict[LangType, LangFile] = {}

    @classmethod
    def __load_i2languages(cls):
        if cls._full_file:
            return

        timeit = Timeit()
        print("Loading I2Languages")

        i2lang = MetaDataHandler.get_path_by_name_no_meta(I2_LANGUAGES)
        assert i2lang

        with open(i2lang, "r", encoding="utf-8") as f:
            cls._full_file = LangFile(COMPOUND_DATA, raw_text=f.read())

        print(f"Loaded I2Languages {timeit!r}")

    @classmethod
    def __load_separate(cls):
        cls.__load_i2languages()

        if cls._loaded_data:
            return


        timeit = Timeit()
        print("Initializing lang files")

        loaded_data: dict[LangType, Any] = {lang_type: OrderedDict() for lang_type in LangType.get_all_types()}
        full_data = cls._full_file.data()["mSource"]["mTerms"]

        for i, lang_entry in enumerate(full_data):
            lang_type_str, *full_key = lang_entry["Term"].replace("{", "").replace("}", "/").split("/")
            lang_type = LangType(lang_type_str) if lang_type_str in LangType else LangType.NONE

            values = loaded_data[lang_type]
            for key in full_key[:-1]:
                if key not in values:
                    values[key] = OrderedDict()
                values = values[key]
            values[full_key[-1]] = [
                e.replace(" ", " ").strip() if isinstance(e, str) else e
                for e in lang_entry["Languages"]
            ]

        for lang_type, values in loaded_data.items():
            cls._loaded_data[lang_type] = LangFile(lang_type, data=values)

        print(f"Initialized lang files {timeit!r}")

    @classmethod
    def get_i2language(cls) -> LangFile:
        cls.__load_i2languages()
        return cls._full_file

    @classmethod
    def get_lang_list(cls, is_str: bool = False) -> list[Lang]:
        i2l = cls.get_i2language().data()
        langs = [Lang(e['Code']) for e in i2l["mSource"]["mLanguages"]]
        if is_str:
            langs = list(map(lambda lang: lang.value, langs))
        return langs

    @classmethod
    def get_lang_file(cls, lang_type: LangType) -> LangFile | None:
        cls.__load_separate()
        return cls._loaded_data.get(lang_type)


def gen_changed_list_to_dict(lang_type: LangType) -> dict[str, Any]:
    lang_list = LangHandler.get_lang_list(True)

    out_data = OrderedDict()

    for key, val in LangHandler.get_lang_file(lang_type).data().items():
        if isinstance(val, list):
            out_data[key] = dict(zip(lang_list, val))
        else:
            out_data[key] = OrderedDict()
            for key2, val2 in val.items():
                out_data[key][key2] = dict(zip(lang_list, val2))

    return out_data


def gen_inverse_dict(lang_type: LangType, selected_langs: set[int] = None) -> OrderedDict[Lang, Any]:
    timeit = Timeit()
    print(f"Generating inverse lang for {lang_type}")

    lang_list = LangHandler.get_lang_list()

    e_lang_list = enumerate(lang_list)
    if selected_langs:
        e_lang_list = [(i, x) for i, x in e_lang_list if i in selected_langs]

    out_data = OrderedDict()

    for i, lang in e_lang_list:
        out_data[lang] = OrderedDict()
        for key, val in LangHandler.get_lang_file(lang_type).data().items():
            if isinstance(val, list):
                out_data[lang][key] = val[i]
            else:
                out_data[lang][key] = OrderedDict()
                for key2, val2 in val.items():
                    out_data[lang][key][key2] = val2[i]

    print(f"Generated inverse lang for {lang_type} {timeit!r}")

    return out_data


if __name__ == "__main__":
    # LangHandler.get_i2language().data()
    a = gen_inverse_dict(LangType.ITEM, {0, 7})
    print(a.keys())
