# -*- coding: utf-8 -*-
# @Author: Catofes
# @Date:   2015-08-15


'''
Class to stores everything into a json file.
'''

from const import Constant
import json

class Singleton(object):
    """Singleton Class
    This is a class to make some class being a Singleton class.
    Such as database class or config class.

    usage:
        class xxx(Singleton):
            def __init__(self):
                if hasattr(self, '_init'):
                    return
                self._init = True
                other init method
    """
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            orig = super(Singleton, cls)
            cls._instance = orig.__new__(cls, *args, **kwargs)
        return cls._instance


class Storage(Singleton):
    def __init__(self):
        """
        Database stores every info.

        version int
        #if value in file is unequal to value defined in this class. An database update will be applied.
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
        player_info dict:
            player_list list:
                songs_id(int)
            playing_list list:
                songs_id(int)
            playing_mode int
            playing_offset int


        :return:
        """
        if hasattr(self, '_init'):
            return
        self._init = True
        self.version = 1
        self.database = {
            "version": 1,
            "user": {
                "username": "",
                "password": "",
            },
            "collections": [[]],
            "songs": {},
            "player_info": {
                "player_list": [],
                "player_list_type": "",
                "player_list_title": "",
                "playing_list": [],
                "playing_mode": 0,
                "idx": 0,
                "ridx": 0,
                "playing_volume": 60,
            },
        }
        self.storage_path = Constant.conf_dir + "/database.json"
        self.file = None

    def load(self):
        try:
            self.file = file(self.storage_path, 'r')
            self.database = json.loads(self.file.read())
            self.file.close()
        except:
            self.__init__()
        self.check_version()

    def check_version(self):
        if self.database["version"] == self.version:
            return
        else:
            #Should do some update. Like    if self.database["version"] == 2 : self.database.["version"] = 3
            pass
            return self.check_version()

    def save(self):
        self.file = file(self.storage_path, 'w')
        self.file.write(json.dumps(self.database))
        self.file.close()



