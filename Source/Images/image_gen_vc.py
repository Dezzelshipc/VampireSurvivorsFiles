from Source.Config.config import Game
from Source.Data.meta_data import MetaDataHandler
from Source.Utility.constants import CARD_GROUP_DATABASE, IMAGES_FOLDER, GENERATED
from Source.Utility.multirun import run_multiprocess_single
from Source.Utility.unityparser2 import UnityDoc


def get_card_group_database():
    card_path = MetaDataHandler.get_path_by_name_no_meta(CARD_GROUP_DATABASE)
    assert card_path, "Not found card database"
    card_meta = UnityDoc.yaml_parse_file(card_path)

    assets_list = card_meta.entries[0].data["_assetList"]

    paths = (MetaDataHandler.get_path_by_guid_no_meta(asset["guid"]) for asset in assets_list)

    def get_asset_data(path):
        doc = UnityDoc.yaml_parse_file(path)
        data = doc.entries[0].data
        return data

    return map(get_asset_data, paths)


def generate_card_group_database():
    assets = get_card_group_database()

    save_folder = IMAGES_FOLDER / GENERATED / CARD_GROUP_DATABASE
    save_folder.mkdir(parents=True, exist_ok=True)

    for asset in assets:
        name = asset["groupName"]
        icon = asset["icon"]
        icon_id = icon["fileID"]
        if icon_id == 0:
            print(f"{name} has no associated icon sprite ({icon})")
            continue
        icon_guid = icon["guid"]

        icon_meta = MetaDataHandler.get_meta_by_guid(icon_guid)
        icon_meta.init_sprites()

        if icon_id not in icon_meta.data_id:
            continue

        icon_meta.data_id[icon_id].sprite.save(save_folder / f"CSprite-{name}.png")

        pass
