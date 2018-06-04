#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: omi
# @Date:   2014-08-24 22:08:33
# @Last Modified by:   omi
# @Last Modified time: 2015-03-30 23:36:21

'''
__   ___________________________________________
| \  ||______   |   |______|_____||______|______
|  \_||______   |   |______|     |______||______

________     __________________________  _____ _     _
|  |  ||     ||______  |  |      |_____]|     | \___/
|  |  ||_____|______|__|__|_____ |_____]|_____|_/   \_


+ ------------------------------------------ +
|   NetEase-MusicBox               320kbps   |
+ ------------------------------------------ +
|                                            |
|   ++++++++++++++++++++++++++++++++++++++   |
|   ++++++++++++++++++++++++++++++++++++++   |
|   ++++++++++++++++++++++++++++++++++++++   |
|   ++++++++++++++++++++++++++++++++++++++   |
|   ++++++++++++++++++++++++++++++++++++++   |
|                                            |
|   A sexy cli musicbox based on Python      |
|   Music resource from music.163.com        |
|                                            |
|   Built with love to music by omi          |
|                                            |
+ ------------------------------------------ +

'''
import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
about = {}  # type: dict

with open(os.path.join(here, 'NEMbox', '__version__.py'), 'r') as f:
    exec(f.read(), about)

setup(
    name=about['__title__'],
    version=about['__version__'],
    author=about['__author__'],
    author_email=about['__author_email__'],
    url=about['__url__'],
    description=about['__description__'],
    license=about['__license__'],
    packages=find_packages(),
    install_requires=[
        'requests-cache',
        'pycryptodomex',
        'future',
    ],
    entry_points={
        'console_scripts': [
            'musicbox = NEMbox:start'
        ],
    },
    keywords=['music', 'netease', 'cli', 'player'],
)
