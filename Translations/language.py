import yaml
import json
import os


def generator_split_to_files(languages: dict, lang_list: list):
    folder_to_save = os.path.normpath(os.path.split(__file__)[0] + '/Generated/Split')

    languages = languages["MonoBehaviour"]["mSource"]["mTerms"]

    full_d = dict()

    total_len = len(languages)

    for i, lang_string in enumerate(languages):
        yield i, total_len

        full_key = lang_string["Term"].split("/")

        group_name = full_key[0]
        if group_name not in full_d:
            full_d.update({group_name: {}})
            for index, lang in lang_list:
                full_d[group_name].update({lang: {}})

        is_part_object = "{" in full_key[1] or "}" in full_key[1]
        id_key = full_key[1].replace("{", "").split("}")

        for index, lang in lang_list:
            entry = lang_string["Languages"][index]

            if isinstance(entry, str):
                entry = entry.replace(" ", " ").strip()

                if "char" in group_name:
                    to_upper_list = ["prefix", "charName", "surname"]
                    if id_key[1] in to_upper_list:
                        entry = entry[0].upper() + entry[1:]

            if is_part_object:
                if len(id_key) < 2:
                    continue

                entry_id = id_key[0].strip()
                if entry_id not in full_d[group_name][lang]:
                    full_d[group_name][lang].update({entry_id: {}})

                full_d[group_name][lang][entry_id].update({id_key[1]: entry})

            else:
                full_d[group_name][lang].update({full_key[1]: entry})

    for group_name in full_d.keys():
        if not os.path.exists(folder_to_save):
            os.makedirs(folder_to_save)

        with open(f'{folder_to_save}/{group_name}.json', 'w', encoding="UTF-8") as part_file:
            part_file.write(json.dumps(full_d[group_name], ensure_ascii=False, indent=2))


def split_to_files(languages: dict, lang_list: list, is_gen=False):
    gen = generator_split_to_files(languages, lang_list)

    if is_gen:
        return gen
    else:
        for _ in gen:
            pass


def get_lang_path(file_name):
    if not file_name:
        return None
    p_dir = __file__.split(os.sep)
    return "\\".join(p_dir[:-2] + ['Translations', 'Generated', 'Split', file_name])


def get_lang_file(path):
    if not path:
        return None
    with open(path, 'r', encoding="UTF-8") as f:
        return json.loads(f.read())


if __name__ == "__main__":
    with open('I2Languages.yaml', 'r', encoding="UTF-8") as file:
        yaml_file = yaml.safe_load(file)

    a = split_to_files(yaml_file, [(0, "en"), (7, "ru")])
