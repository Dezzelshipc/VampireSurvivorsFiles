import os
import shutil
import sys
import time
from pathlib import Path
from tkinter.messagebox import showerror

import requests

from Source.Config.config import DLCType, CfgKey, Config
from Source.Utility.constants import RIPPER_FOLDER, to_source_path
from Source.Utility.timer import Timeit

ripper_port = 56636
ripper_url = f"http://127.0.0.1:{ripper_port}/"


def rip_files(dlc_list: set[DLCType]):
    ripper_path = Config[CfgKey.RIPPER]
    settings_name = "AssetRipper.Settings.json"

    ripper = None
    ripper_settings = None
    this_settings = to_source_path(RIPPER_FOLDER) / settings_name

    try:
        ripper = next(ripper_path.rglob("AssetRippe*.exe"))
    except StopIteration:
        pass

    try:
        ripper_settings = next(ripper_path.rglob("AssetRipper.Setting*[!(old)].json"))
    except StopIteration:
        pass

    if not ripper:
        _s = "AssetRipper not found"
        print(_s, file=sys.stderr)
        showerror("Ripper Error", _s)
        return

    if Config[CfgKey.STEAM_VS] == Path():
        _s = f"Steam config path is empty"
        showerror("Ripper Error", _s)
        print(_s, file=sys.stderr)
        return

    if empty_paths := [dlc.value.full_name for dlc in dlc_list if Config[dlc.value.config_key] == Path()]:
        _s = f"Some config paths are empty:\n{'\n'.join(empty_paths)}"
        showerror("Ripper Error", _s)
        print(_s, file=sys.stderr)
        return

    is_working = True
    try:
        requests.get(ripper_url)
    except requests.ConnectionError:
        is_working = False

    if not is_working:
        # copy existing setting, save as 'old' and copy needed settings in folder
        if not ripper_settings:
            ripper_settings = ripper_path.joinpath(settings_name)
            shutil.copy(this_settings, ripper_settings)

        else:
            old_ripper_settings = ripper_settings.with_suffix(".old.json")
            if not old_ripper_settings.exists():
                shutil.copy(ripper_settings, old_ripper_settings)

            with open(this_settings, "r") as settings_from:
                with open(ripper_settings, "w") as settings_to:
                    settings_to.write(settings_from.read())

        os.startfile(ripper, "open", f"--port {ripper_port} --launch-browser=false")

        wait_time = 1
        while wait_time < 10:
            time.sleep(wait_time)
            try:
                requests.get(ripper_url)
                break
            except requests.ConnectionError:
                wait_time *= 2
                print(f"Ripper is not loaded. Trying reconnect in {wait_time} sec.")

    steam_folder = {p.name: p for p in Config[CfgKey.STEAM_VS].iterdir()}

    for dlc in sorted(map(lambda x: x.value, dlc_list)):
        assets_path = Config[dlc.config_key]

        if dlc.steam_index not in steam_folder:
            print(f"Skipping {dlc.code_name} - Steam folder {dlc.steam_index} not found")
            continue

        print(dlc.code_name, "Loading to", assets_path, end="... ", flush=True)

        timeit = Timeit()

        requests.post(ripper_url + "LoadFolder", data={"Path": steam_folder[dlc.steam_index]})

        assets_path.mkdir(parents=True, exist_ok=True)
        print("Exporting UnityProject", end="... ")
        requests.post(ripper_url + "Export/UnityProject", data={"Path": assets_path})

        # os.makedirs(f"{assets_path}_PrimaryContent", exist_ok=True)
        # print("Exporting PrimaryContent", end="... ")
        # requests.post(ripper_url + "Export/PrimaryContent", data={"Path": f"{assets_path}_PrimaryContent"})

        print(f" ({timeit:.2f} sec) Resetting")
        requests.post(ripper_url + "Reset")


if __name__ == "__main__":
    # rip_files({DLCType.MS, DLCType.OG, DLCType.FS})
    pass
