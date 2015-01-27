NetEase-MusicBox
=================
###Thanks vellow,hbprotoss,Catofes,尘埃

高品质网易云音乐命令行版本，简洁优雅，丝般顺滑，基于Python编写。

![NetEase-MusicBox](http://sdut-zrt.qiniudn.com/687474703a2f2f692e696d6775722e636f6d2f4a35333533764b2e676966.gif)

### 功能特性

1. 320kps的高品质音乐
2. 歌曲，艺术家，专辑检索
3. 网易热门歌曲排行榜
4. 网易新碟推荐
5. 网易精选歌单
6. 网易DJ节目
7. 私人歌单
8. 随心打碟
9. 本地收藏（不提供下载）
10. Vimer式快捷键让操作丝般顺滑
11. 可使用数字快捷键

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
	<tr> <td>P</td> <td>Present</td> <td>当前播放列表</td> </tr>
	<tr> <td>A</td> <td>Add</td> <td>添加曲目到打碟</td> </tr>
	<tr> <td>Z</td> <td>DJ list</td> <td>打碟列表</td> </tr>
	<tr> <td>S</td> <td>Star</td> <td>添加到收藏</td> </tr>
	<tr> <td>C</td> <td>Collection</td> <td>收藏列表</td> </tr>
	<tr> <td>R</td> <td>Remove</td> <td>删除当前条目</td> </tr>
	<tr> <td>Q</td> <td>Quit</td> <td>退出</td> </tr>
	<tr> <td>W</td> <td>Quit&Clear</td> <td>退出并清除用户信息</td> </tr>
</table>

	


### Mac安装

	$ git clone https://github.com/darknessomi/musicbox.git  
	
	$ cd musicbox
	
	$ sudo python setup.py install

	$ brew install mpg123

### Linux安装

	$ git clone https://github.com/darknessomi/musicbox.git  
	
	$ cd musicbox
	
	$ sudo python setup.py install

	$ sudo apt-get install mpg123

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

2015-1-8 版本 0.1.2.4    修改搜索UI (感谢尘埃提交)

2015-1-8 版本 0.1.2.3    增加手气不错,微调音量控制

2015-1-8 版本 0.1.2.0    增加音量控制

2015-1-3 版本 0.1.1.1    修复部分仅手机注册用户登录无法登陆 (感谢Catofes反馈)

2015-1-2 版本 0.1.1.0    新增退出并清除用户信息功能

### The MIT License (MIT)

CopyRight (c) 2014 omi  &lt;<a href="4399.omi@gmail.com">4399.omi@gmail.com</a>&gt;

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

