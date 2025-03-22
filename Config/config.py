from enum import Enum
import json
import os

from dataclasses import dataclass

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from tkinter.messagebox import showerror
from typing import Self

from Utility.singleton import Singleton


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

    IS = "IS_ASSETS"

    def __str__(self):
        return self.value

    @classmethod
    def get_non_path_keys(cls) -> set[Self]:
        return {cls.MULTIPROCESSING}


@dataclass(order=True, unsafe_hash=True)
class DLC:
    index: int
    config_key: CfgKey
    code_name: str
    steam_index: str
    full_name: str


class DLCType(Enum):
    VS = DLC(0, CfgKey.VS, "BASE_GAME", "VampireSurvivors_Data", "Vampire Survivors")
    MS = DLC(1, CfgKey.MS, "MOONSPELL", "2230760", "Legacy of the Moonspell")
    FS = DLC(2, CfgKey.FS, "FOSCARI", "2313550", "Tides of the Foscari")
    EM = DLC(3, CfgKey.EM, "CHALCEDONY", "2690330", "Emergency Meeting")
    OG = DLC(4, CfgKey.OG, "FIRST_BLOOD", "2887680", "Operation Guns")
    OC = DLC(5, CfgKey.OC, "THOSE_PEOPLE", "3210350", "Ode to Castlevania")
    # IS = DLC(6, CfgKey.IS, "-", "-", "IS")

    def __str__(self):
        return self.value.full_name

    def __repr__(self):
        val = self.value
        return f"<{DLCType.__name__}.{self.name} - {val.code_name} - {val.full_name}>"

    @classmethod
    def get_all(cls) -> list[Self]:
        dlcs = [*cls]
        return list(sorted(dlcs, key=lambda x: x.value))

    @classmethod
    def get_by_config(cls, config_key: CfgKey) -> DLC | None:
        for dlc in [*cls]:
            if dlc.value.config_key == config_key:
                return dlc.value
        return None

    @staticmethod
    def get_dlc_name(config_key: CfgKey) -> str | None:
        dlc = DLCType.get_by_config(config_key)
        return dlc.full_name if dlc else None

    @staticmethod
    def get_code_name(config_key: CfgKey) -> str | None:
        dlc = DLCType.get_by_config(config_key)
        return dlc.code_name if dlc else None

    @classmethod
    def get(cls, index: int) -> Self | None:
        _all = cls.get_all()
        return _all[index] if index < len(_all) else None


class Config(metaclass=Singleton):
    class ConfigChanger(tk.Toplevel):
        def __init__(self, parent, config):
            super().__init__(parent)
            self.title("Parsing")
            self.geometry("700x500")
            self.config = config

            ttk.Label(self,
                      text="Enter path to ripped dlc assets.\t Must end with '...\\ExportedProject\\Assets' or be empty.").pack()
            ttk.Label(self).pack()

            self.variables = {}

            for key, path in self.config.data.items():
                if "ASSETS" in key.value:
                    dlc = DLCType.get_by_config(key)
                    if dlc is None:
                        continue

                    tk.Label(self, text=f"{key}\t{dlc.full_name}, {dlc.code_name}").pack()
                    str_var = tk.StringVar(self, path)
                    tk.Entry(self, textvariable=str_var, width=100).pack()
                    self.variables.update({key: str_var})

            key = CfgKey.MULTIPROCESSING
            bool_var_mp = tk.BooleanVar(self, config[key])
            tk.Checkbutton(self, text="Enable multiprocessing for some generators", variable=bool_var_mp).pack()
            self.variables.update({key: bool_var_mp})

            key = CfgKey.RIPPER
            tk.Label(self, text=f"{key}\tAsset Ripper. Folder must contain 'AssetRipper[...].exe'").pack()
            str_var_ripper = tk.StringVar(self, config[key])
            tk.Entry(self, textvariable=str_var_ripper, width=100).pack()
            self.variables.update({key: str_var_ripper})

            key = CfgKey.STEAM_VS
            tk.Label(self, text=f"{key}\tVS steam folder. Folder must contain 'Vampire Survivors.exe'").pack()
            str_var_steam = tk.StringVar(self, config[key])
            tk.Entry(self, textvariable=str_var_steam, width=100).pack()
            self.variables.update({key: str_var_steam})

            ttk.Button(
                self,
                text="Save",
                command=self.try_save
            ).pack()

        def try_save(self):
            variables = {}
            for key, str_var in self.variables.items():
                if "ASSETS" in key.value:
                    var: str | Path = str_var.get() or ""

                    if var in ["\\"] or len(var) < 2:
                        var = ""

                    if var and not var.endswith("Assets"):
                        showerror("Error",
                                  f"Every path to DLC must end with 'Assets' or be empty.\nError in {key}")
                        return

                    if var:
                        var = Path(var)

                    variables.update({key: var})

                elif CfgKey.RIPPER == key:
                    var = str_var.get()
                    if var:
                        if not os.path.exists(var):
                            showerror("Error", "Asset Ripper path does not exists")
                            return

                        is_in = False
                        for p in os.scandir(var):
                            if 'AssetRipper' in p.name and '.exe' in p.name:
                                is_in = True
                                break

                        if not is_in:
                            showerror("Error", "'AssetRipper[...].exe' does not exists")
                            return

                        var = Path(var)

                    variables.update({key: var})

                elif CfgKey.STEAM_VS == key:
                    var = str_var.get()
                    if var:
                        if not os.path.exists(var + "\\VampireSurvivors.exe"):
                            showerror("Error", "Path to 'VampireSurvivors.exe' in steam folder does not exist")
                            return

                        var = Path(var)

                    variables.update({key: var})

                else:
                    variables.update({key: self.variables[key].get()})

            if not os.path.exists(self.config.config_path):
                self.config.save_file()

            self.variables = variables
            self.save()

        def save(self):
            self.config.data.update(self.variables)
            self.config.save_file(self.variables)
            self.destroy()

    def __init__(self):
        self.data: dict[CfgKey: str | None] = dict()
        path = Path(__file__).parent
        self.config_path = path.joinpath("Config.json")

        if not os.path.exists(self.config_path):
            self.save_file()

        self.update_config()

    def update_config(self):
        with open(self.config_path, "r", encoding="UTF-8") as f:
            try:
                json_file = json.loads(f.read())
            except json.decoder.JSONDecodeError as e:
                print(e)
                json_file = {}

            self.data.update({dlc.value.config_key: "" for dlc in DLCType.get_all()})
            self.data.update({CfgKey(k): (v if CfgKey(k) in CfgKey.get_non_path_keys() else Path(v)) for k, v in json_file.items() if k in CfgKey})

    def save_file(self, data: dict | None = None):
        with open(self.config_path, "w", encoding="UTF-8") as f:
            f.write(json.dumps({k.value: ( str(v) if isinstance(v, Path) else v  ) for k, v in (data or {}).items()}, ensure_ascii=False, indent=2))

    def __getitem__(self, item) -> Path | str:
        self.update_config()
        return self.data.get(item)

    def change_config(self, parent):
        self.ConfigChanger(parent, self)

    def get_multiprocessing(self):
        return self["MULTIPROCESSING"]


if __name__ == "__main__":
    cfg = Config()
    print(cfg["VS_ASSETS"])
