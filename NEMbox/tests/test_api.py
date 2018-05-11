#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from future.builtins import str
from NEMbox.api import NetEase


class TestApi(unittest.TestCase):
    def test_api(self):
        ne = NetEase()
        self.assertIsInstance(ne.songs_detail_new_api([27902910])[0]['url'], str)
        self.assertIsNone(ne.songs_detail([405079776])[0]['mp3Url'])  # old api
