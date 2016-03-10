#test branch
NetEase-MusicBox
=================


#### Thanks vellow, hbprotoss, Catofes, 尘埃, chaserhkj, Ma233, 20015jjw, mchome, stkevintan, ayanamimcy

高品质网易云音乐命令行版本，简洁优雅，丝般顺滑，基于Python编写。

[![](https://img.shields.io/pypi/dm/NetEase-MusicBox.svg)](https://pypi.python.org/pypi/NetEase-MusicBox/)
[![Software License](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE.txt) 
[![versions](https://img.shields.io/pypi/v/NetEase-MusicBox.svg)](https://pypi.python.org/pypi/NetEase-MusicBox/)
[![platform](https://img.shields.io/badge/python-2.7-green.svg)]()

[![NetEase-MusicBox](http://7j1yv3.com1.z0.glb.clouddn.com/preview.gif)](https://pypi.python.org/pypi/NetEase-MusicBox/)

### 功能特性

1. 320kbps的高品质音乐
2. 歌曲，艺术家，专辑检索
3. 网易22个歌曲排行榜
4. 网易新碟推荐
5. 网易精选歌单
6. 网易DJ节目
7. 私人歌单，每日推荐
8. 随心打碟
9. 本地收藏，随时加❤
10. 播放进度及播放模式显示
11. Vimer式快捷键让操作丝般顺滑
12. 可使用数字快捷键
13. 可使用自定义全局快捷键

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

	


### Mac安装
	
	$ sudo pip install NetEase-MusicBox

	$ brew install mpg123

### Linux安装
	
	$ sudo pip2 install NetEase-MusicBox

	$ sudo apt-get install mpg123	
	
#### 可选功能依赖 && 配置文件

1. ``` aria2 ``` 用于缓存歌曲
2. ``` python-keybinder ``` 用于支持全局快捷键
3. ``` libnotify-bin ``` 用于支持消息提示

配置文件地址: ``` ~/.netease-musicbox ```  
由于歌曲 API 只接受中国大陆地区访问，港澳台及海外用户请自行在```config.json```中设置代理

```
"mpg123_parameters": {
    "default": [], 
    "describe": "The additional parameters when mpg123 start.", 
    "value": ["-p", "http://ip:port"]
}
```

#### 已测试的系统兼容列表

<table>
	<tr> <td>OS X</td> <td>10.11 / 10.10 / 10.9</td> </tr>
	<tr> <td>Ubuntu</td> <td>14.04</td> </tr>
	<tr> <td>Kali</td> <td>1.1.0 / 2.0</td> </tr>
	<tr> <td>CentOS</td> <td>7</td> </tr>
	<tr> <td>openSUSE</td> <td>13.2</td> </tr>
	<tr> <td>Fedora</td> <td>22</td> </tr>
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

2015-12-02 版本 0.2.0.6    新增手动缓存功能

2015-11-28 版本 0.2.0.5    错误修复

2015-11-10 版本 0.2.0.4    优化切换歌曲时歌单显示, 新增显示歌曲信息功能

2015-11-09 版本 0.2.0.2    修复崩溃错误, 优化榜单排序

2015-11-05 版本 0.2.0.1    优化列表翻页功能

2015-10-31 版本 0.2.0.0    新增部分操作的提醒功能

2015-10-28 版本 0.1.9.9    修复缓存链接过期问题

2015-10-17 版本 0.1.9.8    新增歌曲播放提醒开关

2015-10-14 版本 0.1.9.7    新增歌曲播放提醒

2015-10-13 版本 0.1.9.6    修复因 cookie 过期导致的登陆问题

2015-10-13 版本 0.1.9.5    新增自定义全局快捷键功能

2015-09-25 版本 0.1.9.4    修复部分列表无法暂停问题

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


