# encoding: UTF-8

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import open
from future import standard_library
standard_library.install_aliases()
import json
import os

from . import logger
from .singleton import Singleton
from .const import Constant
from .utils import utf8_data_to_file

log = logger.getLogger(__name__)


class Config(Singleton):

    def __init__(self):
        if hasattr(self, '_init'):
            return
        self._init = True
        self.config_file_path = Constant.config_path
        self.default_config = {
            'version': 7,
            'cache': {
                'value': False,
                'default': False,
                'describe': ('A toggle to enable cache function or not. '
                             'Set value to true to enable it.')
            },
            'mpg123_parameters': {
                'value': [],
                'default': [],
                'describe': 'The additional parameters when mpg123 start.'
            },
            'aria2c_parameters': {
                'value': [],
                'default': [],
                'describe': ('The additional parameters when '
                             'aria2c start to download something.')
            },
            'music_quality': {
                'value': 0,
                'default': 0,
                'describe': ('Select the quality of the music. '
                             'May be useful when network is terrible. '
                             '0 for high quality, 1 for medium and 2 for low.')
            },
            'global_play_pause': {
                'value': '<ctrl><alt>p',
                'default': '<ctrl><alt>p',
                'describe': 'Global keybind for play/pause.'
                            'Uses gtk notation for keybinds.'
            },
            'global_next': {
                'value': '<ctrl><alt>j',
                'default': '<ctrl><alt>j',
                'describe': 'Global keybind for next song.'
                            'Uses gtk notation for keybinds.'
            },
            'global_previous': {
                'value': '<ctrl><alt>k',
                'default': '<ctrl><alt>k',
                'describe': 'Global keybind for previous song.'
                            'Uses gtk notation for keybinds.'
            },
            'notifier': {
                'value': True,
                'default': True,
                'describe': 'Notifier when switching songs.'
            },
            'translation': {
                'value': True,
                'default': True,
                'describe': 'Foreign language lyrics translation.'
            },
            'osdlyrics': {
                'value': False,
                'default': False,
                'describe': 'Desktop lyrics for musicbox.'
            },
            'osdlyrics_transparent': {
                'value': False,
                'default': False,
                'describe': 'Desktop lyrics transparent bg.'
            },
            'osdlyrics_color': {
                'value': [225, 248, 113],
                'default': [225, 248, 113],
                'describe': 'Desktop lyrics RGB Color.'
            },
            'osdlyrics_font': {
                'value': ['Decorative', 16],
                'default': ['Decorative', 16],
                'describe': 'Desktop lyrics font-family and font-size.'
            },
            'osdlyrics_background': {
                'value': 'rgba(100, 100, 100, 120)',
                'default': 'rgba(100, 100, 100, 120)',
                'describe': 'Desktop lyrics background color.'
            },
            'osdlyrics_on_top': {
                'value': True,
                'default': True,
                'describe': 'Desktop lyrics OnTopHint.'
            },
            'curses_transparency': {
                'value': False,
                'default': False,
                'describe': 'Set true to make curses transparency.'
            }
        }
        self.config = {}
        if not os.path.isfile(self.config_file_path):
            self.generate_config_file()
        try:
            f = open(self.config_file_path, 'r')
        except IOError:
            log.debug('Read config file error.')
            return
        try:
            self.config = json.loads(f.read())
        except ValueError:
            log.debug('Load config json data failed.')
            return
        f.close()
        if not self.check_version():
            self.save_config_file()

    def generate_config_file(self):
        f = open(self.config_file_path, 'w')
        utf8_data_to_file(f, json.dumps(self.default_config, indent=2))
        f.close()

    def save_config_file(self):
        f = open(self.config_file_path, 'w')
        utf8_data_to_file(f, json.dumps(self.config, indent=2))
        f.close()

    def check_version(self):
        if self.config['version'] == self.default_config['version']:
            return True
        else:
            # Should do some update. Like
            # if self.database['version'] == 2 : self.database.['version'] = 3
            # update database form version 1 to version 2
            if self.config['version'] == 1:
                self.config['version'] = 2
                self.config['global_play_pause'] = {
                    'value': '<ctrl><alt>p',
                    'default': '<ctrl><alt>p',
                    'describe': 'Global keybind for play/pause.'
                                'Uses gtk notation for keybinds.'
                }
                self.config['global_next'] = {
                    'value': '<ctrl><alt>j',
                    'default': '<ctrl><alt>j',
                    'describe': 'Global keybind for next song.'
                                'Uses gtk notation for keybinds.'
                }
                self.config['global_previous'] = {
                    'value': '<ctrl><alt>k',
                    'default': '<ctrl><alt>k',
                    'describe': 'Global keybind for previous song.'
                                'Uses gtk notation for keybinds.'
                }
            elif self.config['version'] == 2:
                self.config['version'] = 3
                self.config['notifier'] = {
                    'value': True,
                    'default': True,
                    'describe': 'Notifier when switching songs.'
                }
            elif self.config['version'] == 3:
                self.config['version'] = 4
                self.config['translation'] = {
                    'value': True,
                    'default': True,
                    'describe': 'Foreign language lyrics translation.'
                }
            elif self.config['version'] == 4:
                self.config['version'] = 5
                self.config['osdlyrics'] = {
                    'value': False,
                    'default': False,
                    'describe': 'Desktop lyrics for musicbox.'
                }
                self.config['osdlyrics_color'] = {
                    'value': [225, 248, 113],
                    'default': [225, 248, 113],
                    'describe': 'Desktop lyrics RGB Color.'
                }
                self.config['osdlyrics_font'] = {
                    'value': ['Decorative', 16],
                    'default': ['Decorative', 16],
                    'describe': 'Desktop lyrics font-family and font-size.'
                }
                self.config['osdlyrics_background'] = {
                    'value': 'rgba(100, 100, 100, 120)',
                    'default': 'rgba(100, 100, 100, 120)',
                    'describe': 'Desktop lyrics background color.'
                }
                self.config['osdlyrics_transparent'] = {
                    'value': False,
                    'default': False,
                    'describe': 'Desktop lyrics transparent bg.'
                }
            elif self.config['version'] == 5:
                self.config['version'] = 6
                self.config['osdlyrics_on_top'] = {
                    'value': True,
                    'default': True,
                    'describe': 'Desktop lyrics OnTopHint.'
                }
            elif self.config['version'] == 6:
                self.config['version'] = 7
                self.config['curses_transparency'] = {
                    'value': False,
                    'default': False,
                    'describe': 'Set true to make curses transparency.'
                }
            self.check_version()
            return False

    def get_item(self, name):
        if name not in self.config.keys():
            if name not in self.default_config.keys():
                return None
            return self.default_config[name].get('value')
        return self.config[name].get('value')
