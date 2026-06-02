# NetEase-MusicBox

**感谢为 MusicBox 的开发付出过努力的[每一个人](https://github.com/darknessomi/musicbox/graphs/contributors)！**

高品质网易云音乐命令行版本，简洁优雅，丝般顺滑，基于 Python 编写。

感谢 [NeteaseCloudMusicApiEnhanced/api-enhanced](https://github.com/neteasecloudmusicapienhanced/api-enhanced) 项目提供的网易云音乐 API 能力支持。

[![Software License](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE)
[![versions](https://img.shields.io/pypi/v/NetEase-MusicBox.svg)](https://pypi.org/project/NetEase-MusicBox/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/NetEase-MusicBox.svg)](https://pypi.org/project/NetEase-MusicBox/)

## Demo

[![NetEase-MusicBox-GIF](demo.gif)](https://pypi.org/project/NetEase-MusicBox/)

## 功能特性

1. 320kbps 的高品质音乐
2. 歌曲，艺术家，专辑检索
3. 网易 22 个歌曲排行榜
4. 网易新碟推荐
5. 网易精选歌单
6. 网易主播电台
7. 私人歌单，每日推荐
8. 随心打碟
9. 本地收藏，随时加 ❤
10. 播放进度及播放模式显示
11. 现在播放及桌面歌词显示
12. 歌曲评论显示
13. 一键进入歌曲专辑
14. 定时退出
15. Vimer 式快捷键让操作丝般顺滑
16. 可使用数字快捷键
17. 可使用自定义全局快捷键
18. 对当前歌单列表进行本地模糊搜索

### 键盘快捷键

有 num + 字样的快捷键可以用数字修饰，按键顺序为先输入数字再键入被修饰的键，即 num + 后的快捷键。

| Key                                   | Effect          |                    |
| ------------------------------------- | --------------- | ------------------ |
| `j`                                   | Down            | 下移               |
| `k`                                   | Up              | 上移               |
| num + `j`                             | Quick Jump      | 快速向后跳转 n 首  |
| num + `k`                             | Quick Up        | 快速向前跳转 n 首  |
| `h`                                   | Back            | 后退               |
| `l`                                   | Forword         | 前进               |
| `u`                                   | Prev Page       | 上一页             |
| `d`                                   | Next Page       | 下一页             |
| `f`                                   | Search          | 当前列表模糊搜索   |
| `[`                                   | Prev Song       | 上一曲             |
| `]`                                   | Next Song       | 下一曲             |
| num + `[`                             | Quick Prev Song | 快速前 n 首        |
| num + `]`                             | Quick Next Song | 快速后 n 首        |
| num + `Shift` + `g`                   | Index for Song  | 跳到第 n 首        |
| `=`                                   | Volume +        | 音量增加           |
| `-`                                   | Volume -        | 音量减少           |
| `Space`                               | Play/Pause      | 播放/暂停          |
| `?`                                   | Shuffle         | 手气不错           |
| `m`                                   | Menu            | 主菜单             |
| `p`                                   | Present/History | 当前/历史播放列表  |
| `i`                                   | Music Info      | 当前音乐信息       |
| `Shift` + `p`                         | Playing Mode    | 播放模式切换       |
| `a`                                   | Add             | 添加曲目到打碟     |
| `Shift` + `a`                         | Enter Album     | 进入专辑           |
| `g`                                   | To the First    | 跳至首项           |
| `Shift` + `g`                         | To the End      | 跳至尾项           |
| `z`                                   | DJ List         | 打碟列表           |
| `s`                                   | Star            | 添加到收藏         |
| `c`                                   | Collection      | 收藏列表           |
| `r`                                   | Remove          | 删除当前条目       |
| `Shift` + `j`                         | Move Down       | 向下移动当前项目   |
| `Shift` + `k`                         | Move Up         | 向上移动当前项目   |
| `Shift` + `c`                         | Cache           | 缓存歌曲到本地     |
| `,`                                   | Like            | 喜爱               |
| `.`                                   | Trash FM        | 删除 FM            |
| `/`                                   | Next FM         | 下一 FM            |
| `q`                                   | Quit            | 退出               |
| `t`                                   | Timing Exit     | 定时退出           |
| `w`                                   | Quit & Clear    | 退出并清除用户信息 |

## 安装

> 说明：musicbox 是一个命令行**应用**。把它装成全局命令请用 [uv](https://docs.astral.sh/uv/) 或 [pipx](https://pipx.pypa.io/)，它们会为应用创建独立环境并把 `musicbox` 暴露到 PATH。**Poetry 不会安装全局 `musicbox` 命令**，它只用于本仓库的开发调试（见后文）。

**运行环境要求：**

- Python 3.10 及以上（需为正常编译、`hashlib` 完整的解释器）
- `mpg123`（播放歌曲所必需，见下方各平台说明）

### 作为命令行工具安装（推荐普通用户）

```bash
# 从源码安装最新代码（推荐，可获取最新修复，避免 PyPI 版本滞后）
git clone https://github.com/darknessomi/musicbox.git && cd musicbox
uv tool install .          # 或： pipx install .

# 或直接从 PyPI 安装（版本可能滞后）
uv tool install netease-musicbox   # 或： pipx install NetEase-MusicBox
```

安装后直接运行 `musicbox`。

> `uv tool install .` / `pipx install .` 安装的是源码的一份**快照副本**，之后修改源码不会自动生效，需重新执行安装命令。如需源码改动实时生效，用 `uv tool install -e .`。

### 从源码开发 / 调试（使用 Poetry）

Poetry 是依赖与虚拟环境管理工具，**不是应用安装器**，它只会把项目装进自己管理的虚拟环境，无法提供全局 `musicbox` 命令：

```bash
git clone https://github.com/darknessomi/musicbox.git && cd musicbox
poetry env use python3.12      # 可选：指定 3.10+ 解释器（任意路径/命令均可）
poetry install
poetry run musicbox            # 只能在 Poetry 环境内运行
```

### 必选依赖

1. `mpg123` 用于播放歌曲，安装方法参见下面的说明
2. `rapidfuzz` 用于模糊搜索（安装 musicbox 时自动安装）
3. `qrcode` 用于扫码登录时在终端生成二维码（安装 musicbox 时自动安装）

### 可选依赖

1. `aria2` 用于缓存歌曲
2. `libnotify-bin` 用于支持消息提示（Linux 平台）
3. `qtpy python-dbus dbus qt` 用于支持桌面歌词
   (根据系统 qt 的版本还需要安装 pyqt4 pyqt4 pyside pyside2 中的任意一个)

各平台只需先装好系统依赖 `mpg123`，再按上文「作为命令行工具安装」执行 `uv tool install .`（或 pipx）即可。

### macOS

```bash
brew install mpg123 uv      # 若用 pipx 则装 pipx
git clone https://github.com/darknessomi/musicbox.git && cd musicbox
uv tool install .
```

### Linux 安装

#### Ubuntu/Debian

```bash
sudo apt-get install mpg123
# 再按上文「作为命令行工具安装」执行 uv tool install . 或 pipx install .
```

#### Centos/Red Hat

```bash
sudo yum install -y python3-devel mpg123
# 再按上文「作为命令行工具安装」执行 uv tool install . 或 pipx install .
```

### 其他安装方式

以下方式可能不是最新版本，仅作备选。

#### PyPI

```bash
pipx install NetEase-MusicBox   # 或： uv tool install netease-musicbox
```

#### Fedora

首先添加[FZUG](https://github.com/FZUG/repo/wiki)源，然后`sudo dnf install musicbox`。

#### Arch Linux

```bash
pacaur -S netease-musicbox-git # or $ yaourt musicbox
```

## 配置和错误处理

配置文件地址: `~/.config/netease-musicbox/config.json`
可配置缓存，快捷键，消息，桌面歌词。
由于歌曲 API 只接受中国大陆地区访问，非中国大陆地区用户请自行设置代理（可用 polipo 将 socks5 代理转换成 http 代理）：

```bash
export http_proxy=http://IP:PORT
export https_proxy=http://IP:PORT
curl -L ip.cn
```

显示 IP 属于中国大陆地区即可。

### 错误处理

当某些歌曲不能播放时，总时长为 00:01 时，请检查是否为版权问题导致。

如遇到在特定终端下不能播放问题，首先检查**此终端**下 mpg123 能否正常使用，其次检查**其他终端**下 musicbox 能否正常使用，报告 issue 的时候请告知以上使用情况以及出问题终端的报错信息。

同时，您可以通过`tail -f ~/.local/share/netease-musicbox/musicbox.log`自行查看日志。
mpg123 最新的版本可能会报找不到声音硬件的错误，测试了 1.25.6 版本可以正常使用。

### 已知问题及解决方案

- [#374](https://github.com/darknessomi/musicbox/issues/374) i3wm 下播放杂音或快进问题，此问题常见于 Arch Linux。尝试更改 mpg123 配置。
- [#405](https://github.com/darknessomi/musicbox/issues/405) 32 位 Python 下 cookie 时间戳超出了 32 位整数最大值。尝试使用 64 位版本的 Python 或者拷贝 cookie 文件到对应位置。
- [#347](https://github.com/darknessomi/musicbox/issues/347) 暂停时间超过一定长度（数分钟）之后 mpg123 停止输出，导致切换到下一首歌。此问题是 mpg123 的 bug，暂时无解决方案。
- [#791](https://github.com/darknessomi/musicbox/issues/791) 版权问题，master 分支已经修复

## 使用

```bash
    musicbox
```

Enjoy it !

## 登录

登录方式为**扫码登录**，已不再支持账号密码（网易对密码登录强制行为验证码风控，无法在终端内完成）。

进入需要登录的功能（如「我的歌单」）时，终端会显示一个二维码：

1. 用网易云音乐手机 App 扫描二维码，并在手机上点击确认。
2. 登录成功后 Cookie 会保存在 `~/.local/share/netease-musicbox/cookie.txt`（未设置 `XDG_DATA_HOME` 时为 `~/.config/netease-musicbox/cookie.txt`），下次启动自动复用，无需重复扫码。

> 二维码在终端中以字符块渲染，请保证终端窗口足够高（约 25 行以上）并使用等宽字体，否则二维码会被截断而无法扫描。若终端中无法扫描，可复制提示里的 `https://music.163.com/login?codekey=...` 链接，用其他工具生成二维码后再扫。

## 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)

## LICENSE

[MIT](LICENSE)
