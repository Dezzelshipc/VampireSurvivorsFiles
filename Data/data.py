import json
import os
import sys
import re

from Config.config import DLCType

# TODO: Rewrite to some handler-kind

def clean_json(string):
    # extra commas
    string = re.sub(r",[ \t\r\n]+}", "}", string)
    string = re.sub(r",[ \t\r\n]+]", "]", string)

    # comments: //
    string = re.sub(r"\s*//.*\n", "\n", string)
    # comments: /* */
    string = re.sub(r"(?s)/\\*.*?\\*/", "", string)

    return string


def open_f(path):
    return open(path, "r", errors='ignore', encoding="UTF-8-SIG")


def gen_path(paths, name):
    return ([i for i in paths if f"{name}_data" in i.lower()] + [i for i in paths if name in i.lower()] + [""])[0]


def __generator_concatenate(add_content_group=True):
    path = os.path.split(__file__)[0]
    folder_to_save = path + "/Generated"
    os.makedirs(folder_to_save, exist_ok=True)

    names = [f.name.split("_")[0].split('.')[0].lower().replace("data", "") for f in
             os.scandir(path + "/Vampire Survivors")]
    dlcs = list(map(lambda x: x.value.full_name, DLCType.get_all_types()))

    dlc_paths = [[f.path for f in os.scandir(f"{path}/{dlc}")] for dlc in dlcs if os.path.exists(f"{path}/{dlc}")]

    total_len = len(names)

    for i, name in enumerate(names):
        paths = list(filter(lambda x: x, [gen_path(p, name) for p in dlc_paths]))

        cur_p = ""
        try:
            outdata = {}
            index_start = 0
            for p in paths:
                index_cur = 0
                cur_p = p
                with open_f(p) as file:
                    data = json.loads(clean_json(file.read()))
                    # add contentGroup aka dlc
                    if add_content_group and "Data_" in p:
                        file_name = os.path.basename(p).split(".")[0]
                        cg = re.findall('.[^A-Z]*', file_name.split("_")[-1])
                        cg = "_".join([c.upper() for c in cg])

                        has_cg = False
                        for k, v in data.items():
                            vv = v
                            while isinstance(vv, list):
                                vv = vv[0]
                            if vv.get("contentGroup"):
                                has_cg = True
                                break

                        if not has_cg:
                            for k, v in data.items():
                                vv = v
                                while isinstance(vv, list):
                                    vv = vv[0]
                                if not vv.get("contentGroup"):
                                    vv["contentGroup"] = cg

                    same_id = []

                    if "trophy" not in name:
                        for j, (k, v) in enumerate(data.items()):
                            if len(v) <= 0:
                                continue

                            vv = v
                            while isinstance(vv, list) :
                                vv = vv[0]

                            if not all([isinstance(v, (dict, list)) for k, v in vv.items()]):
                                index_cur = j + index_start
                                vv["_index"] = index_cur

                            if outdata.get(k):
                                same_id.append(k)
                                vv["_note"] = f"Found object with same id: {k}. Saved this object with different id"

                    for _id in same_id:
                        new_id = f"{_id}_DOUBLE"
                        data[ new_id  ] = data[ _id ]
                        del data[_id]

                    outdata.update(data)

                index_start = index_cur + 1

            with open(f"{folder_to_save}/{name}Data_Full.json", "w", encoding="UTF-8") as outfile:
                outfile.write(json.dumps(outdata, ensure_ascii=False, indent=2))

        except json.decoder.JSONDecodeError as e:
            print(f"! {name, os.path.basename(cur_p)} skipped: error {e}",
                        file=sys.stderr)

        yield i, total_len


def concatenate(is_gen=False, add_content_group=True):
    gen = __generator_concatenate(add_content_group=add_content_group)

    if is_gen:
        return gen
    else:
        for _ in gen:
            pass


def get_data_path(file_name):
    if not file_name:
        return None
    p_dir = __file__.split(os.sep)
    return "\\".join(p_dir[:-2] + ['Data', 'Generated', file_name])


def get_data_file(path) -> dict | None:
    if not path or not os.path.exists(path):
        return None

    with open(path, 'r', encoding="UTF-8") as f:
        return json.loads(f.read())

def get_all_fields(file_name):
    data = get_data_file(get_data_path(file_name))
    entry = None
    for k, v in data.items():
        entry = v
        break

    fields_data = [{}]

    for _id, vals in data.items():
        lst = vals
        if not isinstance(entry, list):
            lst = [vals]

        for i, d in enumerate(lst):
            if len(fields_data) < i+1:
                fields_data.append({})
            for k, v in d.items():
                if k in fields_data[i]:
                    if type(v) != fields_data[i][k][0]:
                        continue

                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    if k not in fields_data[i]:
                        fields_data[i][k] = [type(v),1e10,-1e10] # type, min, max

                    fields_data[i][k][1] = min(fields_data[i][k][1], v)
                    fields_data[i][k][2] = max(fields_data[i][k][2], v)
                elif isinstance(v, (list, dict)):
                    if k not in fields_data[i]:
                        fields_data[i][k] = [type(v), []]  # type, min, max
                    fields_data[i][k][-1].append(v)
                else:
                    if k not in fields_data[i]:
                        fields_data[i][k] = [type(v), set()]  # type, min, max
                    fields_data[i][k][-1].add(v)

    return fields_data


if __name__ == "__main__":
    # concatenate()
    get_all_fields("characterData_Full.json")