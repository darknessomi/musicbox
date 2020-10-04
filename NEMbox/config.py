# encoding: UTF-8
import json
import os

from .const import Constant
from .singleton import Singleton
from .utils import utf8_data_to_file


class Config(Singleton):
    def __init__(self):
        if hasattr(self, "_init"):
            return
        self._init = True

        self.path = Constant.config_path
        self.default_config = {
            "version": 8,
            "page_length": {
                "value": 10,
                "default": 10,
                "describe": (
                    "Entries each page has. " "Set 0 to adjust automatically."
                ),
            },
            "cache": {
                "value": False,
                "default": False,
                "describe": (
                    "A toggle to enable cache function or not. "
                    "Set value to true to enable it."
                ),
            },
            "mpg123_parameters": {
                "value": [],
                "default": [],
                "describe": "The additional parameters when mpg123 start.",
            },
            "aria2c_parameters": {
                "value": [],
                "default": [],
                "describe": (
                    "The additional parameters when "
                    "aria2c start to download something."
                ),
            },
            "music_quality": {
                "value": 0,
                "default": 0,
                "describe": (
                    "Select the quality of the music. "
                    "May be useful when network is terrible. "
                    "0 for high quality, 1 for medium and 2 for low."
                ),
            },
            "global_play_pause": {
                "value": "<ctrl><alt>p",
                "default": "<ctrl><alt>p",
                "describe": "Global keybind for play/pause."
                "Uses gtk notation for keybinds.",
            },
            "global_next": {
                "value": "<ctrl><alt>j",
                "default": "<ctrl><alt>j",
                "describe": "Global keybind for next song."
                "Uses gtk notation for keybinds.",
            },
            "global_previous": {
                "value": "<ctrl><alt>k",
                "default": "<ctrl><alt>k",
                "describe": "Global keybind for previous song."
                "Uses gtk notation for keybinds.",
            },
            "notifier": {
                "value": True,
                "default": True,
                "describe": "Notifier when switching songs.",
            },
            "translation": {
                "value": True,
                "default": True,
                "describe": "Foreign language lyrics translation.",
            },
            "osdlyrics": {
                "value": False,
                "default": False,
                "describe": "Desktop lyrics for musicbox.",
            },
            "osdlyrics_transparent": {
                "value": False,
                "default": False,
                "describe": "Desktop lyrics transparent bg.",
            },
            "osdlyrics_color": {
                "value": [225, 248, 113],
                "default": [225, 248, 113],
                "describe": "Desktop lyrics RGB Color.",
            },
            "osdlyrics_size": {
                "value": [600, 60],
                "default": [600, 60],
                "describe": "Desktop lyrics area size.",
            },
            "osdlyrics_font": {
                "value": ["Decorative", 16],
                "default": ["Decorative", 16],
                "describe": "Desktop lyrics font-family and font-size.",
            },
            "osdlyrics_background": {
                "value": "rgba(100, 100, 100, 120)",
                "default": "rgba(100, 100, 100, 120)",
                "describe": "Desktop lyrics background color.",
            },
            "osdlyrics_on_top": {
                "value": True,
                "default": True,
                "describe": "Desktop lyrics OnTopHint.",
            },
            "curses_transparency": {
                "value": False,
                "default": False,
                "describe": "Set true to make curses transparency.",
            },
            "left_margin_ratio": {
                "value": 5,
                "default": 5,
                "describe": (
                    "Controls the ratio between width and left margin."
                    "Set to 0 to minimize the margin."
                ),
            },
            "right_margin_ratio": {
                "value": 5,
                "default": 5,
                "describe": (
                    "Controls the ratio between width and right margin."
                    "Set to 0 to minimize the margin."
                ),
            },
            "mouse_movement": {
                "value": False,
                "default": False,
                "describe": "Use mouse or touchpad to move.",
            },
            "input_timeout": {
                "value": 500,
                "default": 500,
                "describe": "The time wait for the next key.",
            },
            "colors": {
                "value": {
                    "pair1": [22, 148],
                    "pair2": [231, 24],
                    "pair3": [231, 9],
                    "pair4": [231, 14],
                    "pair5": [231, 237],
                },
                "default": {
                    "pair1": [22, 148],
                    "pair2": [231, 24],
                    "pair3": [231, 9],
                    "pair4": [231, 14],
                    "pair5": [231, 237],
                },
                "describe": "xterm-256color theme.",
            },
            "keymap": {
                "value": {
                    "down": "j",
                    "up": "k",
                    "back": "h",
                    "forward": "l",
                    "prevPage": "u",
                    "nextPage": "d",
                    "search": "f",
                    "prevSong": "[",
                    "nextSong": "]",
                    "jumpIndex": "G",
                    "playPause": " ",
                    "shuffle": "?",
                    "volume+": "+",
                    "volume-": "-",
                    "menu": "m",
                    "presentHistory": "p",
                    "musicInfo": "i",
                    "playingMode": "P",
                    "enterAlbum": "A",
                    "add": "a",
                    "djList": "z",
                    "star": "s",
                    "collection": "c",
                    "remove": "r",
                    "moveDown": "J",
                    "moveUp": "K",
                    "like": ",",
                    "cache": "C",
                    "trashFM": ".",
                    "nextFM": "/",
                    "quit": "q",
                    "quitClear": "w",
                    "help": "y",
                    "top": "g",
                    "bottom": "G",
                    "countDown": "t",
                },
                "describe": "Keys and function.",
            },
        }
        self.config = {}
        if not os.path.isfile(self.path):
            self.generate_config_file()

        with open(self.path, "r") as config_file:
            try:
                self.config = json.load(config_file)
            except ValueError:
                self.generate_config_file()

    def generate_config_file(self):
        with open(self.path, "w") as config_file:
            utf8_data_to_file(config_file, json.dumps(self.default_config, indent=2))

    def save_config_file(self):
        with open(self.path, "w") as config_file:
            utf8_data_to_file(config_file, json.dumps(self.config, indent=2))

    def get(self, name):
        if name not in self.config.keys():
            self.config[name] = self.default_config[name]
            return self.default_config[name]["value"]
        return self.config[name]["value"]
