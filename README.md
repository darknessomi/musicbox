# NetEase-MusicBox-for-Mac

**感谢为 MusicBox 的开发付出过努力的[每一个人](https://github.com/darknessomi/musicbox/graphs/contributors)！**

本仓库为https://github.com/darknessomi/musicbox.git的fork版本,不支持pip安装.

高品质网易云音乐命令行版本，简洁优雅，丝般顺滑，基于Python编写。

[![Software License](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE.txt)
[![versions](https://img.shields.io/pypi/v/NetEase-MusicBox.svg)](https://pypi.org/project/NetEase-MusicBox/)
[![platform](https://img.shields.io/badge/python-2.7-green.svg)](<>)
[![platform](https://img.shields.io/badge/python-3.5-green.svg)](<>)

[![NetEase-MusicBox-GIF](https://qfile.aobeef.cn/3abba3b8a3994ee3d5cd.gif)](https://pypi.org/project/NetEase-MusicBox/)

## 功能特性

1.  320kbps的高品质音乐
2.  歌曲，艺术家，专辑检索
3.  网易22个歌曲排行榜
4.  网易新碟推荐
5.  网易精选歌单
6.  网易主播电台
7.  私人歌单，每日推荐
8.  随心打碟
9.  本地收藏，随时加❤
10. 播放进度及播放模式显示
11. 现在播放及桌面歌词显示
12. 歌曲评论显示
13. 一键进入歌曲专辑
14. 定时退出
15. Vimer式快捷键让操作丝般顺滑
16. 可使用数字快捷键
17. 可使用自定义全局快捷键

### 键盘快捷键

| Key      | Effect          |                    |
| -------- | --------------- | ------------------ |
| j,下键   | Down            | 下移               |
| k,上键   | Up              | 上移               |
| h,左键   | Back            | 后退               |
| l,右键   | Forword         | 前进               |
|num + j   | QuickJump       | 快速向后跳转n首    |
|num + k   | QuickUp         | 快速向前跳转n首    |
|num + \[  | Quick Prev song | 快速前n首          |
|num + ]   | Quick Next Song | 快速后n首          |
|[[[[[...  | constant key [  | 连按[              |
|]]]]]...  | constant key ]  | 连按]              |
|num + ]   | Quick Next Song | 快速后n首          |
|num       | Index for song  | 跳到第n首          |
| u        | Prev page       | 上一页             |
| d        | Next page       | 下一页             |
| f        | Search          | 快速搜索           |
| \[       | Prev song       | 上一曲             |
| ]        | Next song       | 下一曲             |
| =        | Volume +        | 音量增加           |
| -        | Volume -        | 音量减少           |
| Space    | Play/Pause      | 播放/暂停          |
| ?        | Shuffle         | 手气不错           |
| m        | Menu            | 主菜单             |
| p        | Present/History | 当前/历史播放列表  |
| i        | Music Info      | 当前音乐信息       |
| ⇧+p      | Playing Mode    | 播放模式切换       |
| a        | Add             | 添加曲目到打碟     |
| ⇧+a      | Enter album     | 进入专辑           |
| g        | To the first    | 跳至首项           |
| ⇧+g      | To the end      | 跳至尾项           |
| z        | DJ list         | 打碟列表           |
| s        | Star            | 添加到收藏         |
| c        | Collection      | 收藏列表           |
| r        | Remove          | 删除当前条目       |
| ⇧+j      | Move Down       | 向下移动当前项目   |
| ⇧+k      | Move Up         | 向上移动当前项目   |
| ⇧+c      | Cache           | 缓存歌曲到本地     |
| ,        | Like            | 喜爱               |
| .        | Trash FM        | 删除 FM            |
| /        | Next FM         | 下一FM             |
| q        | Quit            | 退出               |
| t        | Timing Exit     | 定时退出           |
| w        | Quit&Clear      | 退出并清除用户信息 |

## 安装

### 必选依赖

1.  `mpg123` 用于播放歌曲，安装方法参见下面的说明

### 可选依赖

1.  `aria2` 用于缓存歌曲
2.  `libnotify-bin` 用于支持消息提示（Linux平台）
3.  `pyqt python-dbus dbus qt` 用于支持桌面歌词 (Mac 用户需要 `brew install qt --with-dbus` 获取支持 DBus 的 Qt)

    

#### Git clone安装master分支（*nix系统）

    $ git clone https://github.com/wangjianyuan10/musicbox.git && cd musicbox
    $ python(3) setup.py install

### macOS安装

    $ brew install mpg123


## 配置和错误处理

配置文件地址: `~/.netease-musicbox/config.json`
可配置缓存，快捷键，消息，桌面歌词。
由于歌曲 API 只接受中国大陆地区访问，非中国大陆地区用户请自行设置代理（可用polipo将socks5代理转换成http代理）：

```bash
export http_proxy=http://IP:PORT
export https_proxy=http://IP:PORT
curl -L ip.cn
```

显示IP属于中国大陆地区即可。

### 已测试的系统兼容列表

| OS       | Version               |
| -------- | --------------------- |
| macOS    | 10.14 |

### 错误处理

当某些歌曲不能播放时，总时长为 00:01 时，请检查是否为版权问题导致。

如遇到在特定终端下不能播放问题，首先检查**此终端**下mpg123能否正常使用，其次检查**其他终端**下musicbox能否正常使用，报告issue的时候请告知以上使用情况以及出问题终端的报错信息。

同时，您可以通过`tail -f ~/.netease-musicbox/musicbox.log`自行查看日志。
mpg123 最新的版本可能会报找不到声音硬件的错误，测试了1.25.6版本可以正常使用。

### 已知问题及解决方案

-   [#374](https://github.com/darknessomi/musicbox/issues/374) i3wm下播放杂音或快进问题，此问题常见于Arch Linux。尝试更改mpg123配置。
-   [#405](https://github.com/darknessomi/musicbox/issues/405) 32位Python下cookie时间戳超出了32位整数最大值。尝试使用64位版本的Python或者拷贝cookie文件到对应位置。
-   [#347](https://github.com/darknessomi/musicbox/issues/347) 暂停时间超过一定长度（数分钟）之后mpg123停止输出，导致切换到下一首歌。此问题是mpg123的bug，暂时无解决方案。
-   [#791](https://github.com/darknessomi/musicbox/issues/791) 版权问题，master分支已经修复

## 使用

    $ musicbox

Enjoy it !


[更多>>](https://github.com/darknessomi/musicbox/blob/master/ChangeLog.md)

## MIT License

Copyright (c) 2018 omi <mailto:4399.omi@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
