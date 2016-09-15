# -*- coding: utf-8 -*-
# @Author: Catofes
# @Date:   2015-08-15
'''
Class to stores everything into a json file.
'''
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import open
from future import standard_library
standard_library.install_aliases()
import json

from .const import Constant
from .singleton import Singleton
from .utils import utf8_data_to_file


class Storage(Singleton):

    def __init__(self):
        '''
        Database stores every info.

        version int
        #if value in file is unequal to value defined in this class.
        #An database update will be applied.
        user dict:
            username str
            key str
        collections list:
            collection_info(dict):
                collection_name str
                collection_type str
                collection_describe str
                collection_songs list:
                    song_id(int)
        songs dict:
            song_id(int) dict:
                song_id int
                artist str
                song_name str
                mp3_url str
                album_name str
                quality str
                lyric str
                tlyric str
        player_info dict:
            player_list list:
                songs_id(int)
            playing_list list:
                songs_id(int)
            playing_mode int
            playing_offset int


        :return:
        '''
        if hasattr(self, '_init'):
            return
        self._init = True
        self.version = 4
        self.database = {
            'version': 4,
            'user': {
                'username': '',
                'password': '',
                'user_id': '',
                'nickname': '',
            },
            'collections': [[]],
            'songs': {},
            'player_info': {
                'player_list': [],
                'player_list_type': '',
                'player_list_title': '',
                'playing_list': [],
                'playing_mode': 0,
                'idx': 0,
                'ridx': 0,
                'playing_volume': 60,
            }
        }
        self.storage_path = Constant.storage_path
        self.cookie_path = Constant.cookie_path
        self.file = None

    def load(self):
        try:
            self.file = open(self.storage_path, 'r')
            self.database = json.loads(self.file.read())
            self.file.close()
        except (ValueError, OSError, IOError):
            self.__init__()
        if not self.check_version():
            self.save()

    def check_version(self):
        if self.database['version'] == self.version:
            return True
        else:
            # Should do some update.
            if self.database['version'] == 1:
                self.database['version'] = 2
                self.database['cache'] = False
            elif self.database['version'] == 2:
                self.database['version'] = 3
                self.database.pop('cache')
            elif self.database['version'] == 3:
                self.database['version'] = 4
                self.database['user'] = {'username': '',
                                         'password': '',
                                         'user_id': '',
                                         'nickname': ''}
            self.check_version()
            return False

    def save(self):
        self.file = open(self.storage_path, 'w')
        db_str = json.dumps(self.database)
        utf8_data_to_file(self.file, db_str)
        self.file.close()
