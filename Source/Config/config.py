import itertools
import json
import tkinter as tk
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from tkinter import ttk
from tkinter.filedialog import askdirectory
from tkinter.messagebox import showerror, showinfo
from typing import Self, Final, OrderedDict, Callable

from Source.Utility.constants import CONFIG_FOLDER, ROOT_FOLDER, COMPOUND_DATA_TYPE, COMPOUND_DATA
from Source.Utility.special_classes import Objectless

ASSETS = "Assets"
EXPORTED_PROJECT = "ExportedProject"


class CfgKey(Enum):
    MULTIPROCESSING = "MULTIPROCESSING"
    RIPPER = "AS_RIPPER"

    STEAM_VS = "STEAM_APP"
    VS = "VS_ASSETS"
    MS = "MS_ASSETS"
    FS = "FS_ASSETS"
    EM = "EM_ASSETS"
    OG = "OG_ASSETS"
    OC = "OC_ASSETS"
    ED = "ED_ASSETS"
    AC = "AC_ASSETS"
    # IS = "IS_ASSETS"

    STEAM_VC = "STEAM_VC"
    VC = "VC_ASSETS"

    def __str__(self):
        return self.value

    @classmethod
    def get_non_path_keys(cls) -> set[Self]:
        return {cls.MULTIPROCESSING}

    @classmethod
    def get_path_keys(cls) -> set[Self]:
        return {*cls}.difference(cls.get_non_path_keys())

    @classmethod
    def get_assets_keys(cls) -> set[Self]:
        return {*cls}.difference({CfgKey.MULTIPROCESSING, CfgKey.RIPPER, CfgKey.STEAM_VS, CfgKey.STEAM_VC})


class Game(Enum):
    VS = 0
    VC = 100

    SPECIAL = -1


@dataclass(order=True, unsafe_hash=True)
class DLC:
    index: int
    config_key: CfgKey
    game: Game
    code_name: str
    steam_index: str
    full_name: str


class DLCType(Enum):
    VS = DLC(0, CfgKey.VS, Game.VS, "BASE_GAME", "VampireSurvivors_Data", "Vampire Survivors")
    MS = DLC(1, CfgKey.MS, Game.VS, "MOONSPELL", "2230760", "Legacy of the Moonspell")
    FS = DLC(2, CfgKey.FS, Game.VS, "FOSCARI", "2313550", "Tides of the Foscari")
    EM = DLC(3, CfgKey.EM, Game.VS, "CHALCEDONY", "2690330", "Emergency Meeting")
    OG = DLC(4, CfgKey.OG, Game.VS, "FIRST_BLOOD", "2887680", "Operation Guns")
    OC = DLC(5, CfgKey.OC, Game.VS, "THOSE_PEOPLE", "3210350", "Ode to Castlevania")
    ED = DLC(6, CfgKey.ED, Game.VS, "EMERALDS", "3451100", "Emerald Diorama")
    AC = DLC(7, CfgKey.AC, Game.VS, "LEMON", "3929770", "Ante Chamber")
    # IS = DLC(-1, CfgKey.IS, Game.VS, "-", "-", "IS")

    VC = DLC(100, CfgKey.VC, Game.VC, "CRAWLERS", "Vampire Crawlers_Data", "Vampire Crawlers")

    @staticmethod
    def string(dlc: Self | COMPOUND_DATA_TYPE) -> str:
        return str(dlc) if dlc != COMPOUND_DATA else dlc.value

    def __str__(self):
        return self.value.full_name

    def __repr__(self):
        val = self.value
        return f"<{DLCType.__name__}.{self.name} - {val.code_name} - {val.full_name}>"

    @classmethod
    def get_all_types(cls) -> list[Self]:
        dlcs = [*cls]
        return list(sorted(dlcs, key=lambda x: x.value))

    @classmethod
    def get_all_types_by_game(cls, game: Game) -> list[Self]:
        dlcs = [c for c in cls if c.value.game == game]
        return list(sorted(dlcs, key=lambda x: x.value))

    @classmethod
    def get_by_cfgkey(cls, config_key: CfgKey) -> DLC | None:
        for dlc in [*cls]:
            if dlc.value.config_key == config_key:
                return dlc.value
        return None

    @staticmethod
    def get_dlc_name(config_key: CfgKey) -> str | None:
        dlc = DLCType.get_by_cfgkey(config_key)
        return dlc.full_name if dlc else None

    @staticmethod
    def get_code_name(config_key: CfgKey) -> str | None:
        dlc = DLCType.get_by_cfgkey(config_key)
        return dlc.code_name if dlc else None

    @classmethod
    def get(cls, index: int) -> Self | None:
        _all = cls.get_all_types()
        return _all[index] if index < len(_all) else None


class Config(Objectless):
    __data: OrderedDict[CfgKey, Path | bool] = OrderedDict()

    _CONFIG_FILE: Final[Path] = CONFIG_FOLDER / "Config.json"

    @classmethod
    def load(cls):
        cls.__data = cls._get_default_config()
        if not cls._CONFIG_FILE.exists():
            cls._CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        else:
            cls._load_config()
            data, _ = cls._fix_assets_path(cls.__data)
            cls.__data = data

    @classmethod
    def _save_config_file(cls):
        with open(cls._CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(json.dumps({
                key.value: ("" if val == Path() else str(val)) if isinstance(val, Path) else val
                for key, val in cls.__data.items()
            }, ensure_ascii=False, indent=2))

    @staticmethod
    def _get_default_config():
        data: OrderedDict[CfgKey, Path | bool] = OrderedDict(
            {dlc.value.config_key: Path() for dlc in DLCType.get_all_types()})
        data[CfgKey.STEAM_VS] = Path()
        data[CfgKey.STEAM_VC] = Path()
        data[CfgKey.RIPPER] = Path()
        data[CfgKey.MULTIPROCESSING] = False
        return data

    @classmethod
    def _load_config(cls):
        with open(cls._CONFIG_FILE, "r", encoding="UTF-8") as f:
            try:
                json_file = json.loads(f.read())
            except json.decoder.JSONDecodeError as e:
                print(e)
                json_file = OrderedDict()

            cls.__data.update({
                CfgKey(key): (val if CfgKey(key) in CfgKey.get_non_path_keys() else Path(val))
                for key, val in json_file.items()
                if key in CfgKey
            })

    @classmethod
    def _update_data(cls, data: OrderedDict[CfgKey, Path | bool]):
        cls.__data.update(data)

    @classmethod
    def get_data(cls) -> OrderedDict[CfgKey, Path | bool]:
        Config.load()
        return cls.__data

    def __class_getitem__(cls, item: CfgKey) -> Path | bool:
        return cls.get_data().get(item)

    @classmethod
    def get_multiprocessing(cls) -> bool:
        return cls[CfgKey.MULTIPROCESSING]

    @classmethod
    def get_assets_dir(cls, dlc: DLCType = DLCType.VS) -> Path:
        return cls[dlc.value.config_key] / EXPORTED_PROJECT / ASSETS

    @staticmethod
    def _fix_assets_path(data: OrderedDict[CfgKey, Path | bool]) -> (OrderedDict[CfgKey, Path | bool], bool):
        is_changed = False

        for key in CfgKey.get_assets_keys():
            path = Path(data.get(key, ""))
            while EXPORTED_PROJECT in str(path) and ASSETS in str(path):
                is_changed = True
                path = path.parent

            if path.name == EXPORTED_PROJECT:
                is_changed = True
                path = path.parent

            data[key] = path

        return data, is_changed

    @classmethod
    def invoke_config_changer(cls, parent: tk.Tk = None):
        Config.load()
        cc = cls.CfgChanger(parent)
        cc.wait_window()

    class CfgChanger(tk.Toplevel):
        def __init__(self, parent):
            super().__init__(parent)
            self.title("Change config")
            # self.geometry("700x600")

            self.variables: dict[CfgKey, tk.StringVar | tk.BooleanVar | None] = dict(zip(
                Config._get_default_config(),
                itertools.cycle((None,))
            ))

            ttk.Label(self, text="Select path where to save ripped assets.").pack()
            ttk.Label(self, text="!! When ripping all data in selected folder WILL BE REMOVED !!").pack()
            ttk.Label(self).pack()

            def select_folder(variable: tk.StringVar) -> Callable[[], None]:
                def _in_func():
                    folder = askdirectory(parent=self, initialdir=Path(variable.get()) or ROOT_FOLDER)
                    if folder:
                        variable.set(str(Path(folder)))

                return _in_func

            for key in self.variables.keys():
                if key in CfgKey.get_non_path_keys():
                    continue

                info_text = ""
                if dlc := DLCType.get_by_cfgkey(key):
                    info_text = f"{dlc.full_name}. {dlc.code_name}"
                else:
                    match key:
                        case CfgKey.RIPPER:
                            info_text = f"Asset Ripper. Folder must contain 'AssetRipper[...].exe'"
                        case CfgKey.STEAM_VS:
                            info_text = f"VS steam folder. Folder must contain 'Vampire Survivors.exe'"
                        case CfgKey.STEAM_VC:
                            info_text = f"VC steam folder. Folder must contain 'Vampire Crawlers.exe'"
                        case CfgKey.MULTIPROCESSING:
                            continue

                tk.Label(self, text=info_text).pack()

                frame = ttk.Frame(self)
                frame.pack()

                path = Config[key]
                path = "" if path == Path() else str(path)
                self.variables[key] = tk.StringVar(frame, path)

                ttk.Label(frame, text=str(key)).pack(side=tk.LEFT)
                ttk.Entry(frame, textvariable=self.variables[key], width=90).pack(side=tk.LEFT)
                ttk.Button(frame, text="Select folder", command=select_folder(self.variables[key])).pack(side=tk.LEFT)

            frame = ttk.Frame(self)
            frame.pack()

            self.variables[CfgKey.MULTIPROCESSING] = tk.BooleanVar(self, Config[CfgKey.MULTIPROCESSING])
            ttk.Checkbutton(frame, text="Enable multiprocessing for some generators",
                            variable=self.variables[CfgKey.MULTIPROCESSING]).pack()

            ttk.Button(self, text="Check paths and/or Save", command=self.try_save).pack()

        def try_save(self):
            # print({k: v.get() for k, v in self.variables.items()})
            data, is_changed = Config._fix_assets_path(OrderedDict(
                {k: Path(v.get()) if isinstance(v, tk.StringVar) else v.get() for k, v in self.variables.items()}
            ))

            for key in CfgKey.get_assets_keys():
                self.variables[key].set(str(Path(data.get(key))))

            if is_changed:
                showinfo("Config changed",
                         f"Removed '{EXPORTED_PROJECT}' and '{ASSETS}' from assets paths. Press button again to save.")

            asset_ripper_path = Path(self.variables[CfgKey.RIPPER].get())
            is_asset_ripper = asset_ripper_path == Path() or any(asset_ripper_path.glob("AssetRippe*.exe"))
            if not is_asset_ripper:
                showerror("Error: AssetRipper", "AssetRipper.exe not found in selected folder.")

            steam_path_vs = Path(self.variables[CfgKey.STEAM_VS].get())
            is_steam_path_vs = steam_path_vs == Path() or any(steam_path_vs.glob(r"*Survivors*exe"))
            if not is_steam_path_vs:
                showerror("Error: VampireSurvivors", "Vampire Survivors.exe not found in selected folder.")

            steam_path_vc = Path(self.variables[CfgKey.STEAM_VC].get())
            is_steam_path_vc = steam_path_vc == Path() or any(steam_path_vc.glob(r"*Crawlers*exe"))
            if not is_steam_path_vc:
                showerror("Error: VampireCrawlers", "Vampire Crawlers.exe not found in selected folder.")

            if is_changed or not is_asset_ripper or not is_steam_path_vs or not is_steam_path_vc:
                return

            self.__save()

        def __save(self):
            data = OrderedDict(
                {k: Path(v.get()) if isinstance(v, tk.StringVar) else v.get() for k, v in self.variables.items()}
            )
            Config._update_data(data)
            Config._save_config_file()
            self.destroy()


if __name__ == "__main__":
    Config.invoke_config_changer()
