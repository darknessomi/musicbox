# NetEase-MusicBox

**感谢为 MusicBox 的开发付出过努力的[每一个人](https://github.com/darknessomi/musicbox/graphs/contributors)！**

高品质网易云音乐命令行版本，简洁优雅，丝般顺滑，基于Python编写。

[![Software License](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE.txt)
[![versions](https://img.shields.io/pypi/v/NetEase-MusicBox.svg)](https://pypi.org/project/NetEase-MusicBox/)
[![platform](https://img.shields.io/badge/python-3.5-green.svg)](<>)

[![NetEase-MusicBox-GIF](https://qfile.aobeef.cn/3abba3b8a3994ee3d5cd.gif)](https://pypi.org/project/NetEase-MusicBox/)

## 正在做的

本 fork 主要修复一些现有的 Bug，添加一些小功能，添加许多新 Bug。

本人不会 `Python`，所以目前并不打算进行大改和重构。
本人使用 Arch Linux 系统，所以可能不会修一些系统相关的 Bug，如果你遇到了问题，欢迎提 PR。

- [ ] 优化按键逻辑，降低时延，提高容错性
- [ ] 将一些分支判断命题抽象成函数减少 `menu.py` 中代码行数
- [ ] 尝试修复 [darknessomi #857](https://github.com/darknessomi/musicbox/issues/857)
      （当前版本无法复现）
- [x] 尝试修复 [darknessomi #816](https://github.com/darknessomi/musicbox/issues/816)
      [darknessomi #829](https://github.com/darknessomi/musicbox/issues/829)
- [x] 尝试实现功能 [darknessomi #828](https://github.com/darknessomi/musicbox/issues/828)
- [x] 修复评论按 `L` 后出现的按键逻辑混乱
- [ ] 每页行数根据终端窗口大小变化，config 中提供 `auto` 选项
- [x] 修复长按 `j` 或 `k` 时歌词颜色闪烁的 Bug

## 可能打算做的

按照可能的实现难度粗略的排序

1. 消减 Unicode glyph 字符数量
1. Nofitication 添加 Action
1. 鼠标左右键的支持
1. 歌曲评论的回复
1. 修复模糊搜索的一堆 Bug
1. 更多配置选项，例如每次显示歌词行数
1. 版权问题的歌曲灰色显示、不自动跳过并显示 notification
1. 歌曲快进快退 [darknessomi #849](https://github.com/darknessomi/musicbox/issues/849)
1. 运行时更改配置
1. 歌曲信息终端内显示，使用 `libcaca/w3m` 显示专辑封面

## 不打算做的

| 不打算做的 | 原因 |
|-|-|
| 后台运行 | [FeelUOwn](https://github.com/feeluown/FeelUOwn) 可以后台运行，但是目前命令行控制功能不太完善 |
| 用 Rofi 和 dmenu 控制 | 以 [FeelUOwn](https://github.com/feeluown/FeelUOwn) 插件或者 [Mopidy](https://github.com/mopidy/mopidy) 插件实现可能会更好 |
| 最小化显示模式 ( i3bar 等的适配 ) | 同上 |
| 容器和可定制界面 | 感觉没必要，也写不出来 |
| 类 VIM 的增量搜索功能和命令 | 要不直接做成 VIM 插件吧 |
| 类似 lsp 的中间层，适配多后端和多前端 | 目前已经有 [FeelUOwn](https://github.com/feeluown/FeelUOwn) 和 [Mopidy](https://github.com/mopidy/mopidy) 这两个项目了）|

## 功能特性

1. 320kbps的高品质音乐
2. 歌曲，艺术家，专辑检索
3. 网易22个歌曲排行榜
4. 网易新碟推荐
5. 网易精选歌单
6. 网易主播电台
7. 私人歌单，每日推荐
8. 随心打碟
9. 本地收藏，随时加❤
10. 播放进度及播放模式显示
11. 现在播放及桌面歌词显示
12. 歌曲评论显示
13. 一键进入歌曲专辑
14. 定时退出
15. Vimer式快捷键让操作丝般顺滑
16. 可使用数字快捷键
17. 可使用自定义全局快捷键

### 键盘快捷键

| Key       | Effect          |                    |
| --------- | --------------- | ------------------ |
| j         | Down            | 下移               |
| k         | Up              | 上移               |
| num + j   | Quick Jump      | 快速向后跳转n首    |
| num + k   | Quick Up        | 快速向前跳转n首    |
| h         | Back            | 后退               |
| l         | Forword         | 前进               |
| u         | Prev Page       | 上一页             |
| d         | Next Page       | 下一页             |
| f         | Search          | 当前列表模糊搜索   |
| \[        | Prev Song       | 上一曲             |
| ]         | Next Song       | 下一曲             |
| num + \[  | Quick Prev Song | 快速前n首          |
| num + ]   | Quick Next Song | 快速后n首          |
| num + G   | Index for Song  | 跳到第n首          |
| =         | Volume +        | 音量增加           |
| -         | Volume -        | 音量减少           |
| Space     | Play/Pause      | 播放/暂停          |
| ?         | Shuffle         | 手气不错           |
| m         | Menu            | 主菜单             |
| p         | Present/History | 当前/历史播放列表  |
| i         | Music Info      | 当前音乐信息       |
| Shift + p | Playing Mode    | 播放模式切换       |
| a         | Add             | 添加曲目到打碟     |
| Shift + a | Enter Album     | 进入专辑           |
| g         | To the First    | 跳至首项           |
| Shift + g | To the End      | 跳至尾项           |
| z         | DJ List         | 打碟列表           |
| s         | Star            | 添加到收藏         |
| c         | Collection      | 收藏列表           |
| r         | Remove          | 删除当前条目       |
| Shift + j | Move Down       | 向下移动当前项目   |
| Shift + k | Move Up         | 向上移动当前项目   |
| Shift + c | Cache           | 缓存歌曲到本地     |
| ,         | Like            | 喜爱               |
| .         | Trash FM        | 删除 FM            |
| /         | Next FM         | 下一FM             |
| q         | Quit            | 退出               |
| t         | Timing Exit     | 定时退出           |
| w         | Quit & Clear    | 退出并清除用户信息 |

## 安装

### 必选依赖

1. `mpg123` 用于播放歌曲，安装方法参见下面的说明
2. `python-fuzzywuzzy` 用于模糊搜索

### 可选依赖

1. `aria2` 用于缓存歌曲
2. `libnotify-bin` 用于支持消息提示（Linux平台）
3. `pyqt python-dbus dbus qt` 用于支持桌面歌词
   (Mac 用户需要 `brew install qt --with-dbus` 获取支持 DBus 的 Qt)
4. `python-levenshtein` 用于模糊搜索

### PyPi安装（*nix系统）

    $ pip(3) install NetEase-MusicBox

### Git clone安装master分支（*nix系统）

    $ git clone https://github.com/darknessomi/musicbox.git && cd musicbox
    $ python(3) setup.py install

### macOS安装

    $ pip(3) install NetEase-MusicBox
    $ brew install mpg123

### Linux安装

#### Fedora

首先添加[FZUG](https://github.com/FZUG/repo/wiki)源，然后`sudo dnf install musicbox`（通过此方法安装可能仍然需要`pip install -U NetEase-MusicBox`更新到最新版）。

#### Ubuntu/Debian

    $ (sudo) pip install NetEase-MusicBox

    $ (sudo) apt-get install mpg123

#### Arch Linux

    $ pacaur -S netease-musicbox-git # or $ yaourt musicbox

#### Centos/Red Hat

    $ (sudo) pip(3) install NetEase-MusicBox
    $ (sudo) wget http://mirror.centos.org/centos/7/os/x86_64/Packages/mpg123-1.25.6-1.el7.x86_64.rpm
    $ (sudo) yum install mpg123-1.25.6-1.el7.x86_64.rpm

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
| Arch     | Rolling               |

### 错误处理

当某些歌曲不能播放时，总时长为 00:01 时，请检查是否为版权问题导致。

如遇到在特定终端下不能播放问题，首先检查**此终端**下mpg123能否正常使用，其次检查**其他终端**下musicbox能否正常使用，报告issue的时候请告知以上使用情况以及出问题终端的报错信息。

同时，您可以通过`tail -f ~/.netease-musicbox/musicbox.log`自行查看日志。
mpg123 最新的版本可能会报找不到声音硬件的错误，测试了1.25.6版本可以正常使用。

### 已知问题及解决方案

- [#374](https://github.com/darknessomi/musicbox/issues/374) i3wm下播放杂音或快进问题，此问题常见于Arch Linux。尝试更改mpg123配置。
- [#405](https://github.com/darknessomi/musicbox/issues/405) 32位Python下cookie时间戳超出了32位整数最大值。尝试使用64位版本的Python或者拷贝cookie文件到对应位置。
- [#347](https://github.com/darknessomi/musicbox/issues/347) 暂停时间超过一定长度（数分钟）之后mpg123停止输出，导致切换到下一首歌。此问题是mpg123的bug，暂时无解决方案。
- [#791](https://github.com/darknessomi/musicbox/issues/791) 版权问题，master分支已经修复

## 使用

    $ musicbox

Enjoy it !

## 更新日志

2018-11-28 版本 0.2.5.4    修复多处错误

2018-06-21 版本 0.2.5.3    修复多处播放错误

2018-06-07 版本 0.2.5.1    修复配置文件错误

2018-06-05 版本 0.2.5.0    全部迁移到新版api，大量错误修复

2018-05-21 版本 0.2.4.3    更新依赖，错误修复

2017-11-28 版本 0.2.4.2    更新获取歌曲列表的api

2017-06-03 版本 0.2.4.1    修正mpg123状态异常导致的cpu占用，增加歌词双行显示功能

2017-03-17 版本 0.2.4.0    修复通知可能造成的崩溃

2017-03-03 版本 0.2.3.9    邮箱用户登录修复

2017-03-02 版本 0.2.3.8    登录接口修复

2016-11-24 版本 0.2.3.7    新增背景色设置

2016-11-07 版本 0.2.3.6    已知错误修复

2016-10-16 版本 0.2.3.5    新增进入歌曲专辑功能

2016-10-13 版本 0.2.3.4    新增查看歌曲评论

2016-09-26 版本 0.2.3.3    keybinder 错误修复

2016-09-15 版本 0.2.3.2    已知错误修复

2016-09-12 版本 0.2.3.1    已知错误修复

2016-09-11 版本 0.2.3.0    Python 2 和 3 支持

2016-05-09 版本 0.2.2.10   修复最后一行歌名过长的问题

2016-05-08 版本 0.2.2.9    缓存问题修复

2016-05-07 版本 0.2.2.8    解决通知在Gnome桌面持续驻留（#303）的问题

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
