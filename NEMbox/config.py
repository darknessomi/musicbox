# encoding: UTF-8
from __future__ import print_function, unicode_literals, division, absolute_import
import json
import os
from future.builtins import open

from .singleton import Singleton
from .const import Constant
from .utils import utf8_data_to_file


class Config(Singleton):
    def __init__(self):
        if hasattr(self, "_init"):
            return
        self._init = True

        self.path = Constant.config_path
        self.default_config = {
            "version": 8,
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
        }
        self.config = {}
        if not os.path.isfile(self.path):
            self.generate_config_file()

        with open(self.path, "r") as f:
            try:
                self.config = json.load(f)
            except ValueError:
                self.generate_config_file()

    def generate_config_file(self):
        with open(self.path, "w") as f:
            utf8_data_to_file(f, json.dumps(self.default_config, indent=2))

    def save_config_file(self):
        with open(self.path, "w") as f:
            utf8_data_to_file(f, json.dumps(self.config, indent=2))

    def get(self, name):
        if name not in self.config.keys():
            return self.default_config[name]["value"]
        return self.config[name]["value"]
