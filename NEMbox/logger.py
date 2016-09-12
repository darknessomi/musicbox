#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: omi
# @Date:   2014-08-24 21:51:57

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import open
from future import standard_library
standard_library.install_aliases()
import os
import logging

from . import const

FILE_NAME = const.Constant.log_path
if os.path.isdir(const.Constant.conf_dir) is False:
    os.mkdir(const.Constant.conf_dir)

with open(FILE_NAME, 'a+') as f:
    f.write('#' * 80)
    f.write('\n')


def getLogger(name):
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)

    # File output handler
    fh = logging.FileHandler(FILE_NAME)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s:%(lineno)s: %(message)s')
                    )  # NOQA
    log.addHandler(fh)

    return log
