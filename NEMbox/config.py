# encoding: UTF-8

import json
import os
import logger
from singleton import Singleton
from const import Constant


log = logger.getLogger(__name__)


class Config(Singleton):
    def __init__(self):
        if hasattr(self, '_init'):
            return
        self._init = True
        self.const = Constant()
        self.config_file_path = self.const.conf_dir + "/config.json"
        self.default_config = {
            "version": 5,
            "cache": {
                "value": False,
                "default": False,
                "describe": "A toggle to enable cache function or not. Set value to true to enable it."
            },
            "mpg123_parameters": {
                "value": [],
                "default": [],
                "describe": "The additional parameters when mpg123 start."
            },
            "aria2c_parameters": {
                "value": [],
                "default": [],
                "describe": "The additional parameters when aria2c start to download something."
            },
            "music_quality": {
                "value": 0,
                "default": 0,
                "describe": "Select the quality of the music. May be useful at the terrible network connection. "
                            "0 for high quality, 1 for medium and 2 for low."
            },
            "global_play_pause": {
                "value": "<ctrl><alt>p",
                "default": "<ctrl><alt>p",
                "describe": "Global keybind for play/pause."
                            "Uses gtk notation for keybinds."
            },
            "global_next": {
                "value": "<ctrl><alt>j",
                "default": "<ctrl><alt>j",
                "describe": "Global keybind for next song."
                            "Uses gtk notation for keybinds."
            },
            "global_previous": {
                "value": "<ctrl><alt>k",
                "default": "<ctrl><alt>k",
                "describe": "Global keybind for previous song."
                            "Uses gtk notation for keybinds."
            },
            "notifier": {
                "value": True,
                "default": True,
                "describe": "Notifier when switching songs."
            },
            "translation": {
                "value": True,
                "default": True,
                "describe": "Foreign language lyrics translation."
            },
            "osdlyrics": {
                "value": False,
                "default": False,
                "describe": "Desktop lyrics for musicbox."
            },
            "osdlyrics_transparent": {
                "value": False,
                "default": False,
                "describe": "Desktop lyrics transparent bg."
            },
            "osdlyrics_color": {
                "value": [225, 248, 113],
                "default": [225, 248, 113],
                "describe": "Desktop lyrics RGB Color."
            },
            "osdlyrics_font": {
                "value": ['Decorative', 16],
                "default": ['Decorative', 16],
                "describe": "Desktop lyrics font-family and font-size."
            },
            "osdlyrics_background": {
                "value": "rgba(100, 100, 100, 120)",
                "default": "rgba(100, 100, 100, 120)",
                "describe": "Desktop lyrics background color."
            },
        }
        self.config = {}
        if not os.path.isfile(self.config_file_path):
            self.generate_config_file()
        try:
            f = file(self.config_file_path, "r")
        except:
            log.debug("Read config file error.")
            return
        try:
            self.config = json.loads(f.read())
        except:
            log.debug("Load config json data failed.")
            return
        f.close()
        if not self.check_version():
            self.save_config_file()


    def generate_config_file(self):
        f = file(self.config_file_path, "w")
        f.write(json.dumps(self.default_config, indent=2))
        f.close()

    def save_config_file(self):
        f = file(self.config_file_path, "w")
        f.write(json.dumps(self.config, indent=2))
        f.close()

    def check_version(self):
        if self.config["version"] == self.default_config["version"]:
            return True
        else:
            # Should do some update. Like    if self.database["version"] == 2 : self.database.["version"] = 3
            # update database form version 1 to version 2
            if self.config["version"] == 1:
                self.config["version"] = 2
                self.config["global_play_pause"] = {
                    "value": "<ctrl><alt>p",
                    "default": "<ctrl><alt>p",
                    "describe": "Global keybind for play/pause."
                                "Uses gtk notation for keybinds."
                }
                self.config["global_next"] = {
                    "value": "<ctrl><alt>j",
                    "default": "<ctrl><alt>j",
                    "describe": "Global keybind for next song."
                                "Uses gtk notation for keybinds."
                }
                self.config["global_previous"] = {
                    "value": "<ctrl><alt>k",
                    "default": "<ctrl><alt>k",
                    "describe": "Global keybind for previous song."
                                "Uses gtk notation for keybinds."
                }
            elif self.config["version"] == 2:
                self.config["version"] = 3
                self.config["notifier"] = {
                    "value": True,
                    "default": True,
                    "describe": "Notifier when switching songs."
                }
            elif self.config["version"] == 3:
                self.config["version"] = 4
                self.config["translation"] = {
                    "value": True,
                    "default": True,
                    "describe": "Foreign language lyrics translation."
                }
            elif self.config["version"] == 4:
                self.config["version"] = 5
                self.config["osdlyrics"] = {
                    "value": False,
                    "default": False,
                    "describe": "Desktop lyrics for musicbox."
                }
                self.config["osdlyrics_color"] = {
                    "value": [225, 248, 113],
                    "default": [225, 248, 113],
                    "describe": "Desktop lyrics RGB Color."
                }
                self.config["osdlyrics_font"] = {
                    "value": ['Decorative', 16],
                    "default": ['Decorative', 16],
                    "describe": "Desktop lyrics font-family and font-size."
                }
                self.config["osdlyrics_background"] = {
                    "value": "rgba(100, 100, 100, 120)",
                    "default": "rgba(100, 100, 100, 120)",
                    "describe": "Desktop lyrics background color."
                }
            self.check_version()
            return False

    def get_item(self, name):
        if name not in self.config.keys():
            if name not in self.default_config.keys():
                return None
            return self.default_config[name]['value']
        return self.config[name]['value']

