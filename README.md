# NetEase-MusicBox

[![Software License](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE)
![PyPI - Version](https://img.shields.io/pypi/v/NetEase-MusicBox)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/NetEase-MusicBox)


高品质网易云音乐命令行客户端，基于 Python 编写。

感谢为 MusicBox 的开发付出过努力的[每一个人](https://github.com/darknessomi/musicbox/graphs/contributors)。

网易云音乐 API 能力由 [NeteaseCloudMusicApiEnhanced/api-enhanced](https://github.com/neteasecloudmusicapienhanced/api-enhanced) 提供支持。

## Demo

[![NetEase-MusicBox-GIF](demo.gif)](https://pypi.org/project/NetEase-MusicBox/)

## 功能特性

- 支持多档音质播放：MP3（极高/较高/标准）及无损、高清臻音、超清母带等 FLAC，安装 `mpv` 后自动切换
- 支持歌曲、艺术家、专辑、本地列表模糊搜索
- 支持排行榜、新碟上架、精选歌单、主播电台、我的歌单、我的云盘、私人 FM 和每日推荐
- 支持本地收藏、歌曲评论、专辑跳转、随心打碟和定时退出
- 支持播放进度、播放模式、当前/历史播放列表和桌面歌词显示
- 支持 Vim 风格快捷键、数字快捷键和自定义全局快捷键

## 安装

推荐用 [uv](https://docs.astral.sh/uv/) 或 [pipx](https://pipx.pypa.io/) 安装为全局命令 `musicbox`；参与开发见下文「本地开发」。

### 环境要求

- Python 3.10 及以上
- `mpg123`（MP3）、`mpv`（可选，FLAC / Hi-Res）

### 安装系统依赖

macOS:

```bash
brew install mpg123 mpv uv
```

Ubuntu/Debian:

```bash
sudo apt-get install mpg123 mpv
```

CentOS/Red Hat:

```bash
sudo yum install -y python3-devel mpg123 mpv
```

### 安装 MusicBox

**PyPI**（可能落后于源码）：

```bash
uv tool install netease-musicbox
# 或 pipx install NetEase-MusicBox
```

**源码**（全局命令；改代码后需重装，开发期可用 `-e`）：

```bash
git clone https://github.com/darknessomi/musicbox.git
cd musicbox
uv tool install .      # 或 pipx install .
uv tool install -e .   # 可编辑安装，源码改动即时生效
```

**本地开发**（不装全局命令）：

```bash
git clone https://github.com/darknessomi/musicbox.git
cd musicbox
uv sync
uv run musicbox
```

### 可选依赖

- `aria2`：缓存歌曲
- `libnotify-bin`：Linux 消息提示
- `qtpy python-dbus dbus qt`：桌面歌词。根据系统 Qt 版本，可能还需要安装 `pyqt4`、`pyside` 或 `pyside2`

### 树莓派 / 老旧设备

Ubuntu 22.04 / 64 位树莓派系统自带 Python 3.10，可用 `pipx` 直接安装。低性能设备建议先只装 MP3 播放必需依赖，避免一次性拉取 `mpv` 的大量图形/视频依赖：

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends pipx mpg123
pipx ensurepath
pipx install NetEase-MusicBox
musicbox
```

> 注意：项目要求 Python 3.10 及以上；旧版 Raspberry Pi OS / Debian 如果仍是 Python 3.9，不能直接安装当前版本。
>

### 已验证系统

- Ubuntu 24.04 LTS x64
- macOS 26.5
- Raspberry Pi 4 / Ubuntu 22.04 arm64（Docker 镜像：`balenalib/raspberrypi4-64-ubuntu:jammy`）

## 使用

启动 MusicBox：

```bash
musicbox
```

进入需要登录的功能时，终端会显示二维码。登录方式仅支持扫码登录，已不再支持账号密码登录。

1. 用网易云音乐手机 App 扫描二维码，并在手机上确认。
2. 登录成功后 Cookie 写入 `~/.local/share/netease-musicbox/cookie.txt`（未设置 `XDG_DATA_HOME` 时为 `~/.netease-musicbox/cookie.txt`）。

终端以字符块渲染二维码，窗口建议 ≥25 行、等宽字体。必须使用网易云音乐 App 扫描二维码并在手机上确认，不支持打开 URL 完成登录。

## CLI 与 AI Agent

MusicBox 支持命令行和 AI Agent 调用：搜索歌曲、获取播放链接、播放控制、查询状态和登录都可以通过 `musicbox` 命令完成。

```bash
musicbox search 邓丽君 --type song --json
musicbox artist 6452 --limit 10 --json
musicbox album 32311 --json
musicbox song url 1847408145 --quality lossless --quiet
musicbox play --id 1847408145 --json
musicbox play --artist 6452 --limit 10
musicbox play --album 32311
musicbox play --songs 33894312 28258988
musicbox pause --json
musicbox status --json
musicbox queue list --json
musicbox auth login --no-wait --json
musicbox download --playlist 3778678 --path ./music --json
```

```bash
npx skills add darknessomi/musicbox -y
```

安装 Agent Skill 后，可直接让 Codex、Claude Code、Cursor 等 Agent 操作 MusicBox：

```bash
npx skills add darknessomi/musicbox -y
```

## 快捷键

带 `num +` 的快捷键支持数字修饰，先输入数字，再输入被修饰的按键。

| 按键 | 功能 | 说明 |
| --- | --- | --- |
| `j` | Down | 下移 |
| `k` | Up | 上移 |
| `num + j` | Quick Jump | 快速向后跳转 n 首 |
| `num + k` | Quick Up | 快速向前跳转 n 首 |
| `h` | Back | 后退 |
| `l` | Forward | 前进 |
| `u` | Prev Page | 上一页 |
| `d` | Next Page | 下一页 |
| `f` | Search | 当前列表模糊搜索 |
| `[` | Prev Song | 上一曲 |
| `]` | Next Song | 下一曲 |
| `num + [` | Quick Prev Song | 快速前 n 首 |
| `num + ]` | Quick Next Song | 快速后 n 首 |
| `num + Shift + g` | Index for Song | 跳到第 n 首 |
| `=` | Volume + | 音量增加 |
| `-` | Volume - | 音量减少 |
| `Space` | Play/Pause | 播放/暂停 |
| `?` | Shuffle | 手气不错 |
| `m` | Menu | 主菜单 |
| `p` | Present/History | 当前/历史播放列表 |
| `i` | Music Info | 当前音乐信息 |
| `Shift + p` | Playing Mode | 播放模式切换 |
| `a` | Add | 添加曲目到打碟 |
| `Shift + a` | Enter Album | 进入专辑 |
| `g` | To the First | 跳至首项 |
| `Shift + g` | To the End | 跳至尾项 |
| `z` | DJ List | 打碟列表 |
| `s` | Star | 添加到收藏 |
| `c` | Collection | 收藏列表 |
| `r` | Remove | 删除当前条目 |
| `Shift + j` | Move Down | 向下移动当前项目 |
| `Shift + k` | Move Up | 向上移动当前项目 |
| `Shift + c` | Cache | 缓存歌曲到本地 |
| `,` | Like | 喜爱 |
| `.` | Trash FM | 删除 FM |
| `/` | Next FM | 下一 FM |
| `q` | Quit | 退出 |
| `t` | Timing Exit | 定时退出 |
| `w` | Quit & Clear | 退出并清除用户信息 |

## 配置

配置文件位于 `~/.netease-musicbox/config.json`，可配置缓存、快捷键、消息提示和桌面歌词。

无损播放相关配置：

- `music_quality`：音质等级，可填数字或 level 名称。

  | 配置值 | 说明 |
  | --- | --- |
  | `jymaster` | 超清母带，192kHz/24bit |
  | `4` / `hires` | 高清臻音，96kHz/24bit |
  | `3` / `lossless` | 无损，最高 48kHz/16bit |
  | `0` / `exhigh` | 极高，最高 320kbps |
  | `1` / `higher` | 较高，192kbps |
  | `2` / `standard` | 标准，128kbps |

- `player_backend`：默认 `mpg123`；设为 `mpv` 则全程用 `mpv`，否则仅 FLAC 自动切到 `mpv`。
- `mpv_parameters`: 传给 `mpv` 的额外参数列表。

由于歌曲 API 只接受中国大陆地区访问，非中国大陆地区用户需要自行设置代理。可用 polipo 将 socks5 代理转换成 http 代理：

```bash
export http_proxy=http://IP:PORT
export https_proxy=http://IP:PORT
curl -L ip.cn
```

确认显示 IP 属于中国大陆地区即可。

## 排错

- 某些歌曲不能播放且总时长为 `00:01` 时，通常是版权问题。
- 特定终端不能播放时，先检查同一终端下 `mpg123` 能否正常使用，再检查其他终端下 `musicbox` 能否正常使用。报告 issue 时请附上这些检查结果和终端报错。
- 可通过 `tail -f ~/.local/share/netease-musicbox/musicbox.log` 查看日志。



## 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)。

## License

[MIT](LICENSE)
