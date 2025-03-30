import os
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from collections.abc import Iterable
from multiprocessing import Pool
from Config.config import Config


def run_multiprocess(func, args_list: Iterable, is_many_args=True, is_multiprocess=True, processes=None) -> list:
    __config = Config()
    is_config_mp = __config.get_multiprocessing()

    if is_multiprocess and is_config_mp:
        with Pool(processes) as p:
            if is_many_args:
                return p.starmap(func, args_list)
            else:
                return p.map(func, args_list)
    else:
        if is_many_args:
            return [func(*args) for args in args_list]
        else:
            return [func(args) for args in args_list]


class CheckBoxes(tk.Toplevel):
    def __init__(self, list_to_boxes, title="", label="", parent=None, width: int = 300):
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        self.minsize(width, 200)
        label = ttk.Label(self, text=label)
        label.pack()

        self.global_state = tk.BooleanVar()

        cb = ttk.Checkbutton(self, text="Select/Deselect all",
                             variable=self.global_state,
                             command=self.set_all)
        cb.pack()

        self.states = []

        for i, val in enumerate(list_to_boxes):
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(self, text=val, variable=var)
            cb.pack()
            self.states.append(var)

        b_ok = ttk.Button(self, text="Select", command=self.__close)
        b_ok.pack()
        self.return_data = None

    def get_states(self):
        return [v.get() for v in self.states]

    def set_all(self):
        state = self.global_state.get()

        for x in self.states:
            x.set(state)

    def __close(self):
        self.return_data = self.get_states()
        self.destroy()


class ButtonsBox(tk.Toplevel):
    def __init__(self, list_to_texts, title="", label="", parent=None, width: int = 300):
        super().__init__(parent)
        self.parent = parent
        self.minsize(width, 200)
        self.title(title)
        label = ttk.Label(self, text=label)
        label.pack()

        self.return_data = None

        for i, val in enumerate(list_to_texts):
            button = tk.Button(self, text=val, command=self.__close(i))
            button.pack()

    def __close(self, i):
        def f():
            self.return_data = i
            self.destroy()

        return f


def clear_file(save_path: str | os.PathLike[str]):
    with open(save_path, "w+", encoding="UTF-8") as f:
        f.write("")

def write_in_file_end(save_path: str | os.PathLike[str], lines: list[str]):
    with open(save_path, "a+", encoding="UTF-8") as f:
        f.writelines(lines)


def normalize_str(s) -> str:
    s = Path(str(s))
    name = s.name
    try:
        index = name.index('.')
    except ValueError:
        index = None
    return name[:index].lower()
