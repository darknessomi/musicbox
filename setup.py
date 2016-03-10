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
HERE = os.path.abspath(os.path.dirname(__file__))


def get_install_requires(filename):
    req = []
    path = os.path.join(HERE, filename)
    if os.path.exists(path):
        with open(path) as f:
            req = [l.strip() for l in f.xreadlines() if not l.isspace()]
    return req


setup(
    name='NetEase-MusicBox',
    version='0.2.1.6',
    packages=find_packages(),

    include_package_data=True,
    install_requires=get_install_requires('requirements.txt'),

    entry_points={
        'console_scripts': [
            'musicbox = NEMbox:start'
        ],
    },

    author='omi',
    author_email='4399.omi@gmail.com',
    url='https://github.com/darknessomi/musicbox',
    description='A sexy command line interface musicbox',
    keywords=['music', 'netease', 'cli', 'player'],
    zip_safe=False,
)
