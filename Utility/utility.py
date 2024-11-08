import os
import tkinter as tk
from tkinter import ttk
from collections.abc import Iterable
from multiprocessing import Pool
from Config.config import Config, CfgKey


def run_multiprocess(func, args_list: Iterable, is_many_args = True, is_multiprocess = True, processes=None):
    __config = Config()

    if is_multiprocess and __config[CfgKey.MULTIPROCESSING]:
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
    def __init__(self, list_to_boxes, title="", label="", parent=None):
        super().__init__(parent)
        self.parent = parent
        self.title(title)
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
