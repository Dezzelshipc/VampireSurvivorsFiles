import yaml
import json
import os

# en - 0
# ru - 7

if not os.path.isdir('./lang'):
    os.mkdir('./lang')


with open('I2Languages.yaml', 'r', encoding="UTF-8") as file:
    prime = yaml.safe_load(file)

prime = prime["MonoBehaviour"]["mSource"]["mTerms"]

# with open('langAll.json', 'w', encoding="UTF-8") as file:
#     file.write(json.dumps(prime))

prime = prime + [
    {
        "Term": "characterLang/{EXDASH}charName",
        "Languages": ["Exdash"] * 9,
    },
    {
        "Term": "characterLang/{EXDASH}surname",
        "Languages": ["Exiviiq"] * 9,
    },
    {
        "Term": "characterLang/{FINO}charName",
        "Languages": ["missingN▯"] * 9,
    },
    {
        "Term": "characterLang/{FINO}description",
        "Languages": ["M(▯▯)"] * 9,
    }
]

full_d = dict()


for i in prime:
    x = i["Term"].split("/")

    en = i["Languages"][0]
    ru = i["Languages"][7]
    if isinstance(ru, str):
        ru = ru.replace(" ", " ")

    if x[0] not in full_d:
        full_d[x[0]] = {
            "en": {},
            "ru": {}
        }

    if "{" in x[1] or "}" in x[1]:
        y = x[1].replace("{", "").split("}")

        if len(y) < 2:
            continue

        if y[0] not in full_d[x[0]]["en"]:
            full_d[x[0]]["en"][y[0]] = {}
            full_d[x[0]]["ru"][y[0]] = {}

        full_d[x[0]]["en"][y[0]][y[1]] = en
        full_d[x[0]]["ru"][y[0]][y[1]] = ru

    else:
        full_d[x[0]]["en"][x[1]] = en
        full_d[x[0]]["ru"][x[1]] = ru


for k in full_d.keys():
    with open(f'lang/{k}.json', 'w', encoding="UTF-8") as file:
        file.write(json.dumps(full_d[k], ensure_ascii=False, indent=2))