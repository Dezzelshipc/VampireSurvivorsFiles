import shutil
import time
import requests
import os

from Config.config import DLCType, Config, CfgKey

ripper_port = 56636
ripper_url = f"http://127.0.0.1:{ripper_port}/"


def rip_files(dlc_list: set[DLCType]):
    f_path, f_name = os.path.split(__file__)

    config = Config()

    ripper_path = config[CfgKey.RIPPER]
    settings_name = "AssetRipper.Settings.json"

    ripper = None
    ripper_settings = None
    this_settings = os.path.join(f_path, settings_name)

    for p in os.scandir(ripper_path):
        if "AssetRipper" in p.name and ".exe" in p.name:
            ripper = p
        if "Settings" in p.name and ".json" in p.name and "old" not in p.name:
            ripper_settings = p

    is_working = True
    try:
        requests.get(ripper_url)
    except requests.ConnectionError:
        is_working = False

    if not is_working:
        # copy existing setting, save as 'old' and copy needed settings in folder
        if not ripper_settings:
            ripper_settings = os.path.join(ripper_path, settings_name)
            shutil.copy(this_settings, ripper_settings)

        else:
            old_ripper_settings = ripper_settings.path.replace(".json", ".old.json")
            if not os.path.exists(old_ripper_settings):
                shutil.copy(ripper_settings, old_ripper_settings)

            with open(this_settings, "r") as settings_from:
                with open(ripper_settings, "w") as settings_to:
                    settings_to.write(settings_from.read())

        os.startfile(ripper, 'open', f"--port {ripper_port} --launch-browser False")
        time.sleep(0.5)

    remove_from_path = os.path.normpath("\\ExportedProject\\Assets")
    steam_folder = {p.name: p for p in os.scandir(config[CfgKey.STEAM_VS])}

    for dlc in sorted(map(lambda x: x.value, dlc_list)):
        assets_path = (os.path.normpath(config[dlc.config_key]).replace(remove_from_path, ""))

        if dlc.steam_index not in steam_folder:
            print(f"Skipping {dlc.code_name} - Steam folder {dlc.steam_index} not found")
            continue

        print(dlc.code_name, "Loading to", assets_path, end="... ", flush=True)

        time_start_ripping = time.time()

        requests.post(ripper_url + "LoadFolder", data={"Path": steam_folder[dlc.steam_index].path})

        os.makedirs(assets_path, exist_ok=True)
        print("Exporting UnityProject", end="... ")
        requests.post(ripper_url + "Export/UnityProject", data={"Path": assets_path})

        # os.makedirs(f"{assets_path}_PrimaryContent", exist_ok=True)
        # print("Exporting PrimaryContent", end="... ")
        # requests.post(ripper_url + "Export/PrimaryContent", data={"Path": f"{assets_path}_PrimaryContent"})

        print(f" ({round(time.time() - time_start_ripping, 2)} sec) Resetting")
        requests.post(ripper_url + "Reset")


if __name__ == "__main__":
    rip_files({DLCType.MS, DLCType.OG, DLCType.FS})
