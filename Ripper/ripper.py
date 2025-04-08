import shutil
import time
from pathlib import Path

import requests
import os

from Config.config import DLCType, Config, CfgKey
from Utility.timer import Timeit

ripper_port = 56636
ripper_url = f"http://127.0.0.1:{ripper_port}/"


def rip_files(dlc_list: set[DLCType]):
    f_path = Path(__file__).parent

    config = Config()

    ripper_path = config[CfgKey.RIPPER]
    settings_name = "AssetRipper.Settings.json"

    ripper = None
    ripper_settings = None
    this_settings = f_path.joinpath(settings_name)

    for p in ripper_path.iterdir():
        if "AssetRipper" in p.name and ".exe" in p.suffixes:
            ripper = p
        if "Settings" in p.name and ".json" in p.suffixes and "old" not in p.name:
            ripper_settings = p

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

        os.startfile(ripper, "open", f"--port {ripper_port} --launch-browser False")

        wait_time = 1
        while wait_time < 10:
            time.sleep(wait_time)
            try:
                requests.get(ripper_url)
                break
            except requests.ConnectionError:
                wait_time *= 2
                print(f"Ripper is not loaded. Trying reconnect in {wait_time} sec.")


    remove_from_path = ["ExportedProject", "Assets"]
    steam_folder = {p.name: p for p in config[CfgKey.STEAM_VS].iterdir()}

    for dlc in sorted(map(lambda x: x.value, dlc_list)):
        assets_path = config[dlc.config_key]
        while assets_path.stem in remove_from_path:
            assets_path = assets_path.parent

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
