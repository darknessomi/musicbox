Yet Another Music Box
=================

Based on https://github.com/darknessomi/musicbox.

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

### 安装

	$ sudo python2 setup.py install

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

### 使用

	$ musicbox

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
