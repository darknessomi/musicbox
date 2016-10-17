NetEase-MusicBox
=================


#### [感谢](https://github.com/darknessomi/musicbox/graphs/contributors)为 MusicBox 的开发付出过努力的每一个人！

高品质网易云音乐命令行版本，简洁优雅，丝般顺滑，基于Python编写。

[![Software License](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE.txt)
[![versions](https://img.shields.io/pypi/v/NetEase-MusicBox.svg)](https://pypi.python.org/pypi/NetEase-MusicBox/)
[![platform](https://img.shields.io/badge/python-2.7-green.svg)]()
[![platform](https://img.shields.io/badge/python-3.5-green.svg)]()

[![NetEase-MusicBox](http://7j1yv3.com1.z0.glb.clouddn.com/preview.gif)](https://pypi.python.org/pypi/NetEase-MusicBox/)

### 功能特性

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
14. Vimer式快捷键让操作丝般顺滑
15. 可使用数字快捷键
16. 可使用自定义全局快捷键

### 键盘快捷键

<table>
	<tr> <td>J</td> <td>Down</td> <td>下移</td> </tr>
	<tr> <td>K</td> <td>Up</td> <td>上移</td> </tr>
	<tr> <td>H</td> <td>Back</td> <td>后退</td> </tr>
	<tr> <td>L</td> <td>Forword</td> <td>前进</td> </tr>
	<tr> <td>U</td> <td>Prev page</td> <td>上一页</td> </tr>
	<tr> <td>D</td> <td>Next page</td> <td>下一页</td> </tr>
	<tr> <td>F</td> <td>Search</td> <td>快速搜索</td> </tr>
	<tr> <td>[</td> <td>Prev song</td> <td>上一曲</td> </tr>
	<tr> <td>]</td> <td>Next song</td> <td>下一曲</td> </tr>
	<tr> <td>=</td> <td>Volume +</td> <td>音量增加</td> </tr>
	<tr> <td>-</td> <td>Volume -</td> <td>音量减少</td> </tr>
	<tr> <td>Space</td> <td>Play/Pause</td> <td>播放/暂停</td> </tr>
    <tr> <td>?</td> <td>Shuffle</td> <td>手气不错</td> </tr>
	<tr> <td>M</td> <td>Menu</td> <td>主菜单</td> </tr>
	<tr> <td>P</td> <td>Present/History</td> <td>当前/历史播放列表</td> </tr>
	<tr> <td>I</td> <td>Music Info</td> <td>当前音乐信息</td> </tr>
	<tr> <td>⇧+P</td> <td>Playing Mode</td> <td>播放模式切换</td> </tr>
	<tr> <td>A</td> <td>Add</td> <td>添加曲目到打碟</td> </tr>
	<tr> <td>⇧+A</td> <td>Enter album</td> <td>进入专辑</td> </tr>
	<tr> <td>Z</td> <td>DJ list</td> <td>打碟列表</td> </tr>
	<tr> <td>S</td> <td>Star</td> <td>添加到收藏</td> </tr>
	<tr> <td>C</td> <td>Collection</td> <td>收藏列表</td> </tr>
	<tr> <td>R</td> <td>Remove</td> <td>删除当前条目</td> </tr>
	<tr> <td>⇧+J</td> <td>Move Down</td> <td>向下移动当前项目</td> </tr>
	<tr> <td>⇧+K</td> <td>Move Up</td> <td>向上移动当前项目</td> </tr>
	<tr> <td>⇧+C</td> <td>Cache</td> <td>缓存歌曲到本地</td> </tr>
	<tr> <td>,</td> <td>Like</td> <td>喜爱</td> </tr>
	<tr> <td>.</td> <td>Trash FM</td> <td>删除 FM</td> </tr>
	<tr> <td>/</td> <td>Next FM</td> <td>下一FM</td> </tr>
	<tr> <td>Q</td> <td>Quit</td> <td>退出</td> </tr>
	<tr> <td>W</td> <td>Quit&Clear</td> <td>退出并清除用户信息</td> </tr>
</table>




### macOS安装

	$ (sudo) pip install NetEase-MusicBox

	$ brew install mpg123

### Linux安装

#### Fedora
首先添加[FZUG](https://github.com/FZUG/repo/wiki)源，然后`sudo dnf install musicbox`。

#### Ubuntu/Debian

	$ (sudo) pip install NetEase-MusicBox

	$ (sudo) apt-get install mpg123

#### Arch Linux

    $ pacaur -S netease-musicbox-git

#### 可选功能依赖

1. ``` aria2 ``` 用于缓存歌曲
2. ``` python-keybinder ``` 用于支持全局快捷键
3. ``` libnotify-bin ``` 用于支持消息提示
4. ``` pyqt python-dbus dbus qt ``` 用于支持桌面歌词 (Mac 用户需要 ```brew install qt --with-dbus``` 获取支持 DBus 的 Qt)

#### 配置文件
配置文件地址: ``` ~/.netease-musicbox/config.json ```
可配置缓存，快捷键，消息，桌面歌词。
由于歌曲 API 只接受中国大陆地区访问，港澳台及海外用户请自行设置代理：

```
"mpg123_parameters": {
    "default": [],
    "describe": "The additional parameters when mpg123 start.",
    "value": ["-p", "http://ip:port"]
}
```

#### 已测试的系统兼容列表

<table>
	<tr> <td>macOS</td> <td>10.12 / 10.11 / 10.10 / 10.9</td> </tr>
	<tr> <td>Ubuntu</td> <td>14.04</td> </tr>
	<tr> <td>Kali</td> <td>1.1.0 / 2.0 / Rolling</td> </tr>
	<tr> <td>CentOS</td> <td>7</td> </tr>
	<tr> <td>openSUSE</td> <td>13.2</td> </tr>
	<tr> <td>Fedora</td> <td>22</td> </tr>
	<tr> <td>Arch</td> <td>Rolling</td> </tr>
</table>


#### 错误处理

1. pkg_resources.DistributionNotFound: requests

	$ sudo pip install requests

    如果是运行 $ musicbox 出错

	$ sudo pip install --upgrade setuptools

2. pip: Command not found

	$ sudo apt-get install python-pip

3. ImportError: No module named setuptools

    $ sudo easy_install pip

    $ sudo apt-get install python-setuptools

### 使用

	$ musicbox


Enjoy it !

### 更新日志

2016-10-16 版本 0.2.3.5    新增进入歌曲专辑功能

2016-10-13 版本 0.2.3.4    新增查看歌曲评论

2016-09-26 版本 0.2.3.3    keybinder 错误修复

2016-09-15 版本 0.2.3.2    已知错误修复

2016-09-12 版本 0.2.3.1    已知错误修复

2016-09-11 版本 0.2.3.0    Python 2 和 3 支持

2016-05-09 版本 0.2.2.10   修复最后一行歌名过长的问题

2016-05-08 版本 0.2.2.9    缓存问题修复

2016-05-07 版本 0.2.2.8    解决通知在Gnome桌面持续驻留（#303）的问题

2016-05-07 版本 0.2.2.6    已知错误修复

2016-05-05 版本 0.2.2.5    已知错误修复

2016-05-04 版本 0.2.2.4    修复因更换 API 导致版权歌曲播放崩溃

2016-05-04 版本 0.2.2.3    修复部分歌曲跳过问题

2016-04-12 版本 0.2.2.2    修复 OS X 系统桌面歌词置顶和隐藏边框不能共存的问题

[更多>>](Change Log.md)

### The MIT License (MIT)

CopyRight (c) 2015 omi  &lt;<a href="4399.omi@gmail.com">4399.omi@gmail.com</a>&gt;

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
