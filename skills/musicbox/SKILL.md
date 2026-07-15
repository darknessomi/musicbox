---
name: musicbox
description: Use when the user wants to play/pause/skip music, control volume, seek,
  search songs/playlists, query NetEase Music data, or operate NetEase MusicBox.
  Drives MusicBox through the `musicbox` CLI + daemon; never simulates terminal
  keypresses to the curses TUI.
---

# musicbox 控制规则

## 黄金法则

- 通过 `musicbox <cmd> --json` 操作，**绝不**向 curses TUI 模拟按键。
- 重要动作后调 `musicbox status --json` **读回真实状态**再回复用户，不要"发完命令就假设成功"。
- `play` / `next` / `prev` 的即时返回值常滞后（先 `stopped` 或旧进度）；**sleep 1–2 秒后再 `status`** 再下结论。
- 数据类命令（search/artist/album/playlist/toplist/...）无状态，直接调，**不需要** daemon。

## 命令速查

| 类别 | 命令 |
| --- | --- |
| 播放控制 | `play [--id <id>\|--playlist <id>\|--index <n>\|--artist <id>\|--album <id>\|--songs <ids...>]` / `pause` / `resume` / `toggle` / `stop` |
| 切歌/进度 | `next [n]` / `prev [n]` / `seek <秒\|+n\|-n>` |
| 音量/模式 | `volume <0-100\|+n\|-n>` / `mode <ordered\|ordered-loop\|single-loop\|random\|random-loop>` |
| 状态/歌词 | `status` / `lyrics --current` |
| 队列 | `queue list` / `queue add <id...>` / `queue play <index>` / `queue clear --yes` |
| 守护进程 | `daemon start\|stop\|status\|restart` |
| 搜索 | `search <keyword> --type song\|artist\|album\|playlist\|dj` |
| 歌曲/歌单 | `song info <id>` / `song url <id> [--quality lossless]` / `playlist show <id>` |
| 榜单/推荐 | `toplist [--index n]` / `recommend songs\|playlists`（需登录） / `fm`（需登录） |
| 评论/喜爱 | `comments <id>` / `like <id>`（需登录） |
| 查询歌手/专辑 | `artist <id>` / `album <id>` |
| 下载 | `download --artist/--album/--songs/--playlist` |
| 认证/配置 | `auth status\|login\|logout` / `config get <key>` / `config list` |

## 任务配方

### 搜歌并播放

```bash
musicbox search <关键词> --type song --json   # 取 data[0].song_id
musicbox play --id <song_id> --json
# sleep 1–2s
musicbox status --json
```

### 暂停 / 继续

| 当前 `state` | 命令 |
| --- | --- |
| `paused` | `musicbox resume --json` → `status` |
| `stopped` | **不要** `resume`；用 `play --id <id>`、`play --index <n>`，或队列非空时 `play` |
| 换歌/换歌手 | 用 `play --id`，不要假设 `resume` 能接上之前的暂停 |

### 今日推荐（需登录）

```bash
musicbox auth status --json                  # exit 3 则走 login split-flow
musicbox recommend songs --limit 20 --json   # 收集 data[].song_id → ids[]
musicbox play --id <ids[0]> --json
musicbox queue add <ids[1]> <ids[2]> ... --json   # 每个 ID 独立 argv
musicbox mode ordered --json
musicbox status --json
```

`queue add` 在 shell 里勿把多个 ID 拼成一个字符串；可用 `queue add $(printf '%s\n' "${ids[@]:1}")` 或从 JSON 解析后逐个传参。

### 歌单播放

```bash
musicbox play --playlist <playlist_id> --json
musicbox mode ordered --json    # 列表类意图默认顺序播放
musicbox status --json
```

切歌后用 `queue_index` / `queue_size` 确认当前第几首。


### 搜歌手并播放热门歌曲

```bash
musicbox search <关键词> --type artist --json   # 取 data[0].id
musicbox artist <artist_id> --json            # 查看热门歌曲
musicbox play --artist <artist_id> --limit 20 --json   # 播放前 20 首
musicbox status --json
```

### 搜专辑并播放

```bash
musicbox search <关键词> --type album --json    # 取 data[0].id
musicbox album <album_id> --json              # 查看专辑歌曲列表
musicbox play --album <album_id> --json       # 播放整张专辑
musicbox status --json
```

### 播放多首指定歌曲

```bash
musicbox play --songs <id1> <id2> <id3> --json   # 清队列 + 添加歌曲 + 播放第一首
musicbox queue list --json                    # 确认队列内容
musicbox status --json
```

### 下载歌曲

```bash
musicbox download --playlist <playlist_id> --path ./music --json
musicbox download --artist <artist_id> --limit 20 --path ./music --json
musicbox download --album <album_id> --path ./music --json
musicbox download --songs <id1> <id2> --path ./music --json
```

每首歌曲下载为 `<artist> - <song>.mp3`，结果输出 JSON 数组，每项包含 `ok`/错误信息。
## 输出约定

- Agent 调用时**始终加 `--json`**，解析 stdout 的 `{ok, data}` 信封。
- 错误在 stderr：`{ok: false, error: {type, message, hint}}`。
- 管道取值可用 `--quiet`（只输出关键值）。
- `--dry-run`：只打印将发送的 RPC，不产生副作用，用于预演控制命令。

## daemon 生命周期

- 播放是**有状态本地会话**，由常驻 `musicboxd` 守护进程持有；控制类命令经它通信。
- 控制类命令默认**自动拉起 daemon**；若遇 `exit 4`（daemon 未运行），先 `musicbox daemon start` 再重试。
- `--no-daemon-autostart` 可禁用自动拉起（不在跑则直接 `exit 4`）。
- daemon 与 curses TUI **互斥**：TUI 在跑时 daemon 无法启动，反之亦然。
- 本地改过播放/daemon 代码后，先 `musicbox daemon restart`，否则仍是旧进程逻辑。

## status 是你的眼睛

```json
{ "ok": true, "data": {
  "state": "playing|paused|stopped",
  "song": {"id": 33894312, "name": "...", "artist": "...", "album": "...", "duration": 273},
  "position": 41.2, "length": 273, "volume": 60,
  "mode": "ordered", "backend": "mpv", "queue_index": 3, "queue_size": 20
}}
```

## 登录（split-flow，必须分两轮）

1. **本轮**：`musicbox auth login --no-wait --json` → 取 `qr_ascii` / `unikey` → 把二维码发给用户 → 明确告知「用网易云音乐 App 扫码并确认后回来告诉我」→ **结束本轮**。
2. **下一轮**：用户回复后执行 `musicbox auth login --check <unikey> --json`。

纪律：

- **禁止**输出 URL 让用户打开登录；必须使用网易云音乐 App 扫二维码。
- **禁止**同轮展示二维码后立刻阻塞轮询。
- **禁止**跨会话缓存 `unikey`（过期即重新 `login --no-wait`）。

## 退出码分支

| code | 含义 | Agent 应对 |
| --- | --- | --- |
| 0 | 成功 | 继续 |
| 1 | 通用失败 | 读 `error.message` |
| 2 | 参数错误 | 按 `hint` 修正 argv 重试 |
| 3 | 未登录 | 走 `auth login` split-flow |
| 4 | daemon 未运行 | `musicbox daemon start` 后重试（控制类默认会自动拉起） |
| 5 | 操作不支持 | 读 `error.message`（如 mpg123 后端不支持 `seek`） |
| 10 | 高风险写操作需确认 | **先问用户**，再在 argv 末尾追加 `--yes` 重试；绝不静默加 `--yes` |

## 注意事项

- `seek` 仅在 mpv 后端可用；mpg123 后端会返回 `not_supported`（`exit 5`），可提示用户播放无损或将 `player_backend` 设为 `mpv`。
- `queue clear`、`auth logout` 是高风险写操作，遇 `exit 10` 先向用户确认。
- **版权失败**：`state` 为 `stopped` 且日志/通知含 copyright；单曲或无可切下一首时会停止，**不要**对同一首反复 `play`/`next` 重试，直接告知用户换歌。
- 播列表、今日推荐、歌单时，未指定模式则设 `mode ordered`，避免残留 `random-loop` 打乱顺序。
