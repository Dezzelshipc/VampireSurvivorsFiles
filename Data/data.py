import json
import os
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from Config.config import DLCType
from Utility.meta_data import MetaDataHandler
from Utility.singleton import Singleton
from Utility.unityparser2 import UnityDoc
from Utility.utility import clean_json, to_pascalcase


def open_f(path):
    return open(path, "r", errors='ignore', encoding="UTF-8-SIG")


class DataType(Enum):
    ACHIEVEMENT = "Achievement"
    ADVENTURE = "Adventure"
    ADVENTURE_MERCHANTS = "AdventureMerchants"
    ADVENTURE_STAGE_SET = "AdventureStageSet"
    ALBUM = "Album"
    ARCANA = "Arcana"
    CHARACTER = "Character"
    CUSTOM_MERCHANTS = "CustomMerchants"
    ENEMY = "Enemy"
    HIT_VFX = "HitVfx"
    ITEM = "Item"
    LIMIT_BREAK = "LimitBreak"
    MUSIC = "Music"
    POWERUP = "PowerUp"
    PROPS = "Props"
    SECRET = "Secret"
    STAGE = "Stage"
    # TROPHY00 = None
    # TROPHY01 = None
    WEAPON = "Weapon"

    NONE = None

    @staticmethod
    def from_data_file(data_file_key: str) -> "DataType":
        match data_file_key:
            case "_AchievementDataJsonAsset":
                return DataType.ACHIEVEMENT
            case "_ArcanaDataJsonAsset":
                return DataType.ARCANA
            case "_CharacterDataJsonAsset":
                return DataType.CHARACTER
            case "_EnemyDataJsonAsset":
                return DataType.ENEMY
            case "_HitVfxDataJsonAsset":
                return DataType.HIT_VFX
            case "_ItemDataJsonAsset":
                return DataType.ITEM
            case "_LimitBreakDataJsonAsset":
                return DataType.LIMIT_BREAK
            case "_MusicDataJsonAsset":
                return DataType.MUSIC
            case "_PowerUpDataJsonAsset":
                return DataType.POWERUP
            case "_PropsDataJsonAsset":
                return DataType.PROPS
            case "_SecretsDataJsonAsset":
                return DataType.SECRET
            case "_StageDataJsonAsset":
                return DataType.STAGE
            case "_WeaponDataJsonAsset":
                return DataType.WEAPON
            case "_AlbumDataJsonAsset":
                return DataType.ALBUM
            case "_CustomMerchantsDataJsonAsset":
                return DataType.CUSTOM_MERCHANTS
            case "_AdventureDataJsonAsset":
                return DataType.ADVENTURE
            case "_AdventuresStageSetDataJsonAsset":
                return DataType.ADVENTURE_STAGE_SET
            case "_AdventuresMerchantsDataJsonAsset":
                return DataType.ADVENTURE_MERCHANTS
        return DataType.NONE


@dataclass
class DataFile:
    guid: str
    __path: Path
    __data: dict[str, Any] | None = None
    __raw_text: str | None = None

    def __init__(self, guid: str):
        self.guid = guid

    def __load(self):
        if self.__data:
            return

        self.__path = MetaDataHandler().get_path_by_guid_no_meta(self.guid)

        with open_f(self.__path) as f:
            self.__raw_text = f.read()

        self.__data = json.loads(clean_json(self.__raw_text))

    def get_data(self) -> dict[str, Any]:
        self.__load()
        return self.__data

    def get_raw_text(self) -> str:
        self.__load()
        return self.__raw_text


class DataHandler(metaclass=Singleton):
    _loaded_data: dict[DLCType, dict[DataType, DataFile]] = {}

    @classmethod
    def load(cls):
        if cls._loaded_data:
            return

        ## VS: "DataManagerSettings", Other: "BundleManifestData - [code_name (id) in PascalCase]"
        loaded_data = {}

        mdh = MetaDataHandler()
        vs_data = list(mdh.filter_paths(lambda name_path: "DataManagerSettings".lower() in name_path[0]))

        if vs_data:
            doc = UnityDoc.yaml_parse_file(vs_data[0][1].with_suffix(""))
            loaded_data[DLCType.VS] = doc.entries[0].data['_Settings']

        all_dlc_types = DLCType.get_all_types()
        dlc_datas = mdh.filter_paths(lambda name_path: "BundleManifestData".lower() in name_path[0])
        for name, path in dlc_datas:
            for dlc_type in all_dlc_types:
                if to_pascalcase(dlc_type.value.code_name).lower() in name:
                    doc = UnityDoc.yaml_parse_file(path.with_suffix(""))
                    loaded_data[dlc_type] = doc.entries[0].data['_DataFiles']
                    break

        for dlc_type, data in loaded_data.items():
            current_dlc: dict[DataType, DataFile] = {}
            for key, file in data.items():
                if len(file) > 1:
                    current_dlc[DataType.from_data_file(key)] = DataFile(file["guid"])

            cls._loaded_data[dlc_type] = current_dlc

    @classmethod
    def get_dict_by_dlc_type(cls, dlc_type: DLCType) -> dict[DataType, DataFile]:
        cls.load()
        return cls._loaded_data.get(dlc_type)

    @classmethod
    def get_data(cls, dlc_type: DLCType, data_type: DataType) -> DataFile:
        cls.load()
        return cls._loaded_data.get(dlc_type, {}).get(data_type)

    @classmethod
    def get_total_amount(cls) -> int:
        cls.load()
        return sum(len(dfs) for dfs in cls._loaded_data.values())


if __name__ == "__main__":
    DataHandler.load()

########



def gen_path(paths, name):
    return ([i for i in paths if f"{name}_data" in i.lower()] + [i for i in paths if name in i.lower()] + [""])[0]


def __generator_concatenate(add_content_group=True):
    path = os.path.split(__file__)[0]
    folder_to_save = path + "/Generated"
    os.makedirs(folder_to_save, exist_ok=True)

    names = [f.name.split("_")[0].split('.')[0].lower().replace("data", "") for f in
             os.scandir(path + "/Vampire Survivors")]
    dlcs = list(map(lambda x: x.value.full_name, DLCType.get_all_types()))

    dlc_paths = [[f.path for f in os.scandir(f"{path}/{dlc}")] for dlc in dlcs if os.path.exists(f"{path}/{dlc}")]

    total_len = len(names)

    for i, name in enumerate(names):
        paths = list(filter(lambda x: x, [gen_path(p, name) for p in dlc_paths]))

        cur_p = ""
        try:
            outdata = {}
            index_start = 0
            for p in paths:
                index_cur = 0
                cur_p = p
                with open_f(p) as file:
                    data = json.loads(clean_json(file.read()))
                    # add contentGroup aka dlc
                    if add_content_group and "Data_" in p:
                        file_name = os.path.basename(p).split(".")[0]
                        cg = re.findall('.[^A-Z]*', file_name.split("_")[-1])
                        cg = "_".join([c.upper() for c in cg])

                        has_cg = False
                        for k, v in data.items():
                            vv = v
                            while isinstance(vv, list):
                                vv = vv[0]
                            if vv.get("contentGroup"):
                                has_cg = True
                                break

                        if not has_cg:
                            for k, v in data.items():
                                vv = v
                                while isinstance(vv, list):
                                    vv = vv[0]
                                if not vv.get("contentGroup"):
                                    vv["contentGroup"] = cg

                    same_id = []

                    if "trophy" not in name:
                        for j, (k, v) in enumerate(data.items()):
                            if len(v) <= 0:
                                continue

                            vv = v
                            while isinstance(vv, list) :
                                vv = vv[0]

                            if not all([isinstance(v, (dict, list)) for k, v in vv.items()]):
                                index_cur = j + index_start
                                vv["_index"] = index_cur

                            if outdata.get(k):
                                same_id.append(k)
                                vv["_note"] = f"Found object with same id: {k}. Saved this object with different id"

                    for _id in same_id:
                        new_id = f"{_id}_DOUBLE"
                        data[ new_id  ] = data[ _id ]
                        del data[_id]

                    outdata.update(data)

                index_start = index_cur + 1

            with open(f"{folder_to_save}/{name}Data_Full.json", "w", encoding="UTF-8") as outfile:
                outfile.write(json.dumps(outdata, ensure_ascii=False, indent=2))

        except json.decoder.JSONDecodeError as e:
            print(f"! {name, os.path.basename(cur_p)} skipped: error {e}",
                        file=sys.stderr)

        yield i, total_len


def concatenate(is_gen=False, add_content_group=True):
    gen = __generator_concatenate(add_content_group=add_content_group)

    if is_gen:
        return gen
    else:
        for _ in gen:
            pass


def get_data_path(file_name):
    if not file_name:
        return None
    p_dir = __file__.split(os.sep)
    return "\\".join(p_dir[:-2] + ['Data', 'Generated', file_name])


def get_data_file(path) -> dict | None:
    if not path or not os.path.exists(path):
        return None

    with open(path, 'r', encoding="UTF-8") as f:
        return json.loads(f.read())

def get_all_fields(file_name):
    data = get_data_file(get_data_path(file_name))
    entry = None
    for k, v in data.items():
        entry = v
        break

    fields_data = [{}]

    for _id, vals in data.items():
        lst = vals
        if not isinstance(entry, list):
            lst = [vals]

        for i, d in enumerate(lst):
            if len(fields_data) < i+1:
                fields_data.append({})
            for k, v in d.items():
                if k in fields_data[i]:
                    if type(v) != fields_data[i][k][0]:
                        continue

                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    if k not in fields_data[i]:
                        fields_data[i][k] = [type(v),1e10,-1e10] # type, min, max

                    fields_data[i][k][1] = min(fields_data[i][k][1], v)
                    fields_data[i][k][2] = max(fields_data[i][k][2], v)
                elif isinstance(v, (list, dict)):
                    if k not in fields_data[i]:
                        fields_data[i][k] = [type(v), []]  # type, min, max
                    fields_data[i][k][-1].append(v)
                else:
                    if k not in fields_data[i]:
                        fields_data[i][k] = [type(v), set()]  # type, min, max
                    fields_data[i][k][-1].add(v)

    return fields_data

#
# if __name__ == "__main__":
#     # concatenate()
#     get_all_fields("characterData_Full.json")