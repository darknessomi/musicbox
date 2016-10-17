#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from builtins import int
from builtins import chr
from future import standard_library
standard_library.install_aliases()
from time import time
import locale

locale.setlocale(locale.LC_ALL, '')
code = locale.getpreferredencoding()


class scrollstring(object):

    def __init__(self, content, START):
        self.content = content  # the true content of the string
        self.display = content  # the displayed string
        self.START = START // 1  # when this instance is created
        self.update()

    def update(self):
        self.display = self.content
        curTime = time() // 1
        offset = max(int((curTime - self.START) % len(self.content)) - 1, 0)
        while offset > 0:
            if self.display[0] > chr(127):
                offset -= 1
                self.display = self.display[3:] + self.display[:3]
            else:
                offset -= 1
                self.display = self.display[1:] + self.display[:1]

        # self.display = self.content[offset:] + self.content[:offset]

    def __repr__(self):
        return self.display

# determine the display length of a string


def truelen(string):
    """
    It appears one Asian character takes two spots, but __len__
    counts it as three, so this function counts the dispalyed
    length of the string.

    >>> truelen('abc')
    3
    >>> truelen('你好')
    4
    >>> truelen('1二3')
    4
    >>> truelen('')
    0
    """
    return len(string) - sum(1 for c in string if c > chr(127)) / 3
