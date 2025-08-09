import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from Config.config import DLCType
from Utility.constants import DATA_MANAGER_SETTINGS, BUNDLE_MANIFEST_DATA, COMPOUND_DATA
from Utility.meta_data import MetaDataHandler
from Utility.special_classes import Objectless
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
    WEAPON = "Weapon"

    NONE = None

    @classmethod
    def get_all_types(cls) -> set["DataType"]:
        return {*cls}.difference({DataType.NONE})

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
    __data_type: DataType | Literal[COMPOUND_DATA]
    __path: Path
    __to_concat: dict[DLCType, "DataFile"] | None = None
    __data: dict[str, Any] | None = None
    __raw_text: str | None = None

    def __init__(self, data_type: DataType | Literal[COMPOUND_DATA], guid: str | None,
                 data_to_concat: dict[DLCType, "DataFile"] = None):
        self.__data_type = data_type
        self.guid = guid
        self.__to_concat = data_to_concat

    def __load(self):
        if self.__data:
            return

        if not self.__to_concat:
            self.__path = MetaDataHandler().get_path_by_guid_no_meta(self.guid)

            with open_f(self.__path) as f:
                self.__raw_text = f.read()

            self.__data = json.loads(clean_json(self.__raw_text))
        else:
            self.__data = _concatenate(self.__to_concat)
            self.__raw_text = json.dumps(self.__data, ensure_ascii=False, indent=2)

    def data(self) -> dict[str, Any]:
        self.__load()
        return self.__data

    def raw_text(self) -> str:
        self.__load()
        return self.__raw_text

    def data_type(self) -> DataType:
        return self.__data_type


def _concatenate(data_to_concat: dict[DLCType, DataFile]):
    out_data = {}
    index_start = 0
    for dlc_type in DLCType.get_all_types():
        index_cur = 0

        data_file = data_to_concat.get(dlc_type)
        if not data_file:
            continue

        data = data_file.data()

        # add contentGroup aka dlc
        cg = dlc_type.value.code_name

        ## Monster condition ;-)
        has_cg = False or data_file.data_type() == DataType.ADVENTURE_STAGE_SET
        for k, v in data.items():
            vv = v
            while isinstance(vv, list) and vv:
                vv = vv[0]
            if isinstance(vv, dict) and vv.get("contentGroup"):
                has_cg = True
                break

        if not has_cg:
            for k, v in data.items():
                vv = v
                while isinstance(vv, list) and vv:
                    vv = vv[0]
                if isinstance(vv, dict) and not vv.get("contentGroup"):
                    vv["contentGroup"] = cg

        same_id = []

        for j, (k, v) in enumerate(data.items()):
            if len(v) <= 0:
                continue

            vv = v
            while isinstance(vv, list):
                vv = vv[0]

            if not all([isinstance(v, (dict, list)) for k, v in vv.items()]):
                index_cur = j + index_start
                vv["_index"] = index_cur

            if out_data.get(k):
                same_id.append(k)
                vv["_note"] = f"Found object with same id: {k}. Saved this object with different id"

        for _id in same_id:
            new_id = f"{_id}_DOUBLE"
            data[new_id] = data[_id]
            del data[_id]

        out_data.update(data)

        index_start = index_cur + 1

    return out_data


class DataHandler(Objectless):
    _loaded_data: dict[DLCType, dict[DataType, DataFile]] = {}
    _concat_data: dict[DataType, DataFile] = {}

    @classmethod
    def load(cls):
        if cls._loaded_data:
            return

        ## VS: "DataManagerSettings", Other: "BundleManifestData - [code_name (id) in PascalCase]"
        loaded_data = {}

        mdh = MetaDataHandler()
        vs_data = list(mdh.filter_paths(lambda name_path: DATA_MANAGER_SETTINGS.lower() in name_path[0]))

        if vs_data:
            doc = UnityDoc.yaml_parse_file(vs_data[0][1].with_suffix(""))
            loaded_data[DLCType.VS] = doc.entries[0].data['_Settings']

        all_dlc_types = DLCType.get_all_types()
        dlc_datas = mdh.filter_paths(lambda name_path: BUNDLE_MANIFEST_DATA.lower() in name_path[0])
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
                    data_type = DataType.from_data_file(key)
                    current_dlc[data_type] = DataFile(data_type, file["guid"])

            cls._loaded_data[dlc_type] = current_dlc

        for data_type in DataType.get_all_types():
            concat_data: dict[DLCType, DataFile] = {}
            for dlc_type in all_dlc_types:
                concat_data[dlc_type] = cls._loaded_data.get(dlc_type, {}).get(data_type)
            cls._concat_data[data_type] = DataFile(COMPOUND_DATA, None, concat_data)

    @classmethod
    def get_dict_by_dlc_type(cls, dlc_type: DLCType | Literal[COMPOUND_DATA]) -> dict[DataType, DataFile]:
        cls.load()
        if dlc_type == COMPOUND_DATA:
            return cls._concat_data
        else:
            return cls._loaded_data.get(dlc_type)

    @classmethod
    def get_data(cls, dlc_type: DLCType | Literal[COMPOUND_DATA], data_type: DataType | None) -> DataFile:
        cls.load()
        if dlc_type == COMPOUND_DATA:
            return cls._concat_data.get(data_type)
        else:
            return cls._loaded_data.get(dlc_type, {}).get(data_type)

    @classmethod
    def get_total_amount(cls) -> int:
        cls.load()
        return sum(len(dfs) for dfs in cls._loaded_data.values())


if __name__ == "__main__":
    DataHandler.load()


def get_all_fields(dlc_type: DLCType | None, data_type: DataType):
    data = DataHandler.get_data(dlc_type, data_type).data()
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
            if len(fields_data) < i + 1:
                fields_data.append({})
            for k, v in d.items():
                if k in fields_data[i]:
                    if type(v) != fields_data[i][k][0]:
                        continue

                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    if k not in fields_data[i]:
                        fields_data[i][k] = [type(v), 1e10, -1e10]  # type, min, max

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
