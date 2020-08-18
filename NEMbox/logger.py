#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: omi
# @Date:   2014-08-24 21:51:57
from __future__ import print_function, unicode_literals, division, absolute_import
import logging

from future.builtins import open

from . import const

FILE_NAME = const.Constant.log_path


with open(FILE_NAME, "a+") as f:
    f.write("#" * 80)
    f.write("\n")


def getLogger(name):
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)

    # File output handler
    fh = logging.FileHandler(FILE_NAME)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s:%(lineno)s: %(message)s"
        )
    )
    log.addHandler(fh)

    return log
