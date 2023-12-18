import yaml
import json
import os


def generator_split_to_files(languages: dict, lang_list: list, total_lang_count: int,
                             is_add_more=True):
    folder_to_save = os.path.normpath(os.path.split(__file__)[0] + '/Generated/Split')

    languages = languages["MonoBehaviour"]["mSource"]["mTerms"]

    if is_add_more:
        languages = languages + [
            {
                "Term": "characterLang/{EXDASH}charName",
                "Languages": ["Exdash"] * total_lang_count,
            },
            {
                "Term": "characterLang/{EXDASH}surname",
                "Languages": ["Exiviiq"] * total_lang_count,
            },
            {
                "Term": "characterLang/{FINO}charName",
                "Languages": ["missingN▯"] * total_lang_count,
            },
            {
                "Term": "characterLang/{FINO}description",
                "Languages": ["M(▯▯)"] * total_lang_count,
            }
        ]

    full_d = dict()

    total_len = len(languages)

    for i, lang_string in enumerate(languages):
        yield i, total_len

        x = lang_string["Term"].split("/")

        if x[0] not in full_d:
            full_d.update({x[0]: {}})
            for index, lang in lang_list:
                full_d[x[0]].update({lang: {}})

        is_part_object = "{" in x[1] or "}" in x[1]
        y = x[1].replace("{", "").split("}")

        for index, lang in lang_list:
            string = lang_string["Languages"][index]

            if isinstance(string, str):
                string = string.replace(" ", " ")

            if is_part_object:
                if len(y) < 2:
                    continue

                if y[0] not in full_d[x[0]][lang]:
                    full_d[x[0]][lang].update({y[0]: {}})

                full_d[x[0]][lang][y[0]].update({y[1]: string})

            else:
                full_d[x[0]][lang].update({x[1]: string})

    for k in full_d.keys():
        if not os.path.exists(folder_to_save):
            os.makedirs(folder_to_save)

        with open(f'{folder_to_save}/{k}.json', 'w', encoding="UTF-8") as part_file:
            part_file.write(json.dumps(full_d[k], ensure_ascii=False, indent=2))


def split_to_files(languages: dict, lang_list: list, total_lang_count: int,
                   is_add_more=True, is_gen=False):
    gen = generator_split_to_files(languages, lang_list, total_lang_count, is_add_more)

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

    a = split_to_files(yaml_file, [(0, "en"), (7, "ru")], len(yaml_file["MonoBehaviour"]["mSource"]["mLanguages"]))
