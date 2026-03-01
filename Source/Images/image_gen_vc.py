from Source.Data.meta_data import MetaDataHandler
from Source.Utility.constants import CARD_GROUP_DATABASE, IMAGES_FOLDER, GENERATED
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

    asset_groups = {}
    for asset in assets:
        if not (name := asset.get("_assetId")):
            continue

        name = name.replace("CardGroup_", "")
        icon = asset["icon"]
        if icon["fileID"] == 0:
            print(f"{name} has no associated icon sprite ({icon})")
            continue

        group_name = asset["groupName"]
        if group_name not in asset_groups:
            asset_groups[group_name] = []

        asset_groups[group_name].append((name, icon, asset))

    for group_name, assets_in_group in asset_groups.items():

        sf = save_folder
        if len(assets_in_group) > 1:
            sf = sf / group_name
            sf.mkdir(parents=True, exist_ok=True)

        for (name, icon, asset) in assets_in_group:
            if group_name.replace(" ", "").replace("'", "").lower() == name.replace(" ", "").replace("'", "").lower():
                name = group_name

            icon_id = icon["fileID"]
            icon_guid = icon["guid"]

            icon_meta = MetaDataHandler.get_meta_by_guid(icon_guid)
            icon_meta.init_sprites()

            if icon_id not in icon_meta.data_id:
                print(f"{name} has no associated icon sprite ({icon})")
                continue

            icon_meta.data_id[icon_id].sprite.save(sf / f"CSprite-{ name }.png")

