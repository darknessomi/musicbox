#!/usr/bin/env python
# coding=utf-8
# __author__='walker'

"""
捕获类似curses键盘输入流,生成指令流
"""

from copy import deepcopy
from functools import wraps


__all__ = ['cmd_parser', 'parse_keylist', 'coroutine']


def coroutine(func):
    @wraps(func)
    def primer(*args, **kwargs):
        gen = func(*args, **kwargs)
        next(gen)
        return gen
    return primer


def _cmd_parser():
    '''
    A generator receive key value typed by user return constant keylist.
    输入键盘输入流,输出指令流,以curses默认-1为信号终止.
    '''
    pre_key = -1
    keylist = []
    while 1:
        key = yield
        if key*pre_key < 0 and key > pre_key:
            temp_pre_key = key
            keylist.append(key)
        elif key*pre_key > 0 and key+pre_key > 0:
            temp_pre_key = key
            keylist.append(key)
        elif key*pre_key < 0 and key < pre_key:
            temp_pre_key = key
            return keylist
        pre_key = key


def cmd_parser(results):
    '''
    A generator manager which can catch StopIteration and start a new Generator.
    生成器管理对象,可以优雅地屏蔽生成器的终止信号,并重启生成器
    '''
    while 1:
        results.clear()
        results += yield from _cmd_parser()
        # results.clear()
        yield results


def parse_keylist(keylist):
    """
    '2' '3' '4' 'j'  ----> 234 j
    supoort keys  [  ]   j  k  <KEY_UP> <KEY_DOWN>
    """
    keylist = deepcopy(keylist)
    if keylist == []:
        return None
    tail_cmd = keylist.pop()
    if set(keylist) | set(range(48, 58)) == set(range(48, 58)):
        return int(''.join([chr(i) for i in keylist]+[chr(tail_cmd)]))

    if len(keylist) == 0:
        return (0, tail_cmd)
    if tail_cmd in (ord('['), ord(']'), ord('j'), ord('k'), 258, 259) and \
            max(keylist) <= 57 and min(keylist) >= 48:
        return (int(''.join([chr(i) for i in keylist])), tail_cmd)
    return None


def main(data):
    '''
    tset code
    测试代码
    '''
    results = []
    group = cmd_parser(results)
    next(group)
    for i in data:
        group.send(i)
    group.send(-1)
    print(results)
    next(group)
    for i in data:
        group.send(i)
    group.send(-1)
    print(results)


if __name__ == '__main__':
    main(list(range(1, 12,)[::-1]))
