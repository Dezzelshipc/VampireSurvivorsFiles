import json
import os

import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showerror

from Utility.singleton import Singleton


class Config(metaclass=Singleton):
    class ConfigChanger(tk.Toplevel):
        def __init__(self, parent, config):
            super().__init__(parent)
            self.title("Parsing")
            self.geometry("700x400")
            self.config = config

            self.label = ttk.Label(self,
                                   text="Enter path to ripped dlc assets.\t Must end with '...\\ExportedProject\\Assets' or be empty.")
            self.label.pack()

            ttk.Label(self).pack()

            self.variables = {}

            for key, path in self.config.data.items():
                if "ASSETS" in key:
                    tk.Label(self, text=f"{key}\t{config.DLCS[key]}").pack()
                    str_var = tk.StringVar(self, path)
                    tk.Entry(self, textvariable=str_var, width=100).pack()
                    self.variables.update({key: str_var})

            key = "MULTIPROCESSING"
            bool_var_mp = tk.BooleanVar(self, self.config[key])
            tk.Checkbutton(self, text="Enable multiprocessing for some generators", variable=bool_var_mp).pack()
            self.variables.update({key: bool_var_mp})

            save_button = ttk.Button(
                self,
                text="Save",
                command=self.try_save
            )
            save_button.pack()

        def try_save(self):
            variables = {}
            for key, str_var in self.variables.items():
                if "ASSETS" in key:
                    var: str = str_var.get()

                    if not var:
                        var = "\\"

                    if not var.endswith("Assets") and var != "\\" and var != "/":
                        showerror("Error",
                                  f"Every path to DLC must end with 'Assets' or be empty.\nError in {key}")
                        return
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
        self.default = {
            "VS_ASSETS": "/",
            "MS_ASSETS": "/",
            "FS_ASSETS": "/",
            "EM_ASSETS": "/",
            "OG_ASSETS": "/",
            "IS_ASSETS": "/",
            "MULTIPROCESSING": False,
        }
        self.DLCS = {
            "VS_ASSETS": "Vampire Survivors",
            "MS_ASSETS": "Moonspell",
            "FS_ASSETS": "Foscari",
            "EM_ASSETS": "Meeting",
            "OG_ASSETS": "Guns",
            "IS_ASSETS": "TBA",
        }
        self.data = self.default.copy()
        self.config_path = os.path.join(os.path.split(__file__)[0], "Config.json")

        if not os.path.exists(self.config_path):
            self.save_file()

        self.update_config()

    def update_config(self):
        with open(self.config_path, "r", encoding="UTF-8") as f:
            json_file = json.loads(f.read())
            self.data.update(json_file)

    def save_file(self, data: dict | None = None):
        with open(self.config_path, "w", encoding="UTF-8") as f:
            f.write(json.dumps(data or self.default, ensure_ascii=False, indent=2))

    def __getitem__(self, item) -> str:
        self.update_config()
        return self.data.get(item, self.default.get(item))

    def change_config(self, parent):
        self.ConfigChanger(parent, self)

    def get_dlc_name(self, item) -> str | None:
        return self.DLCS.get(item, None)


if __name__ == "__main__":
    cfg = Config()
    print(cfg["VS_ASSETS"])
