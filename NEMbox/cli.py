"""Agent-friendly CLI for MusicBox (phase 1: stateless data commands)."""

from __future__ import annotations

import argparse
import contextlib
import curses
import io
import json
import sys
from typing import Any

from . import __version__
from .api import NetEase
from .config import Config
from .daemon import (
    is_daemon_running,
    send_request,
    spawn_daemon,
    stop_daemon,
)
from .storage import Storage

# Exit codes (aligned with docs/agent-cli-design.md)
EXIT_OK = 0
EXIT_GENERIC = 1
EXIT_INVALID_ARGS = 2
EXIT_NOT_LOGGED_IN = 3
EXIT_DAEMON_NOT_RUNNING = 4
EXIT_NOT_SUPPORTED = 5
EXIT_CONFIRM_REQUIRED = 10

# Map daemon error.type -> CLI exit code.
_ERROR_EXIT_CODES = {
    "invalid_args": EXIT_INVALID_ARGS,
    "not_logged_in": EXIT_NOT_LOGGED_IN,
    "daemon_not_running": EXIT_DAEMON_NOT_RUNNING,
    "not_supported": EXIT_NOT_SUPPORTED,
    "confirmation_required": EXIT_CONFIRM_REQUIRED,
}

MODE_CHOICES = [
    "ordered",
    "ordered-loop",
    "single-loop",
    "random",
    "random-loop",
]

SEARCH_TYPES = {
    "song": (1, "songs"),
    "artist": (100, "artists"),
    "album": (10, "albums"),
    "playlist": (1000, "playlists"),
    "dj": (1009, "djRadios"),
}

LOGIN_STATUS = {
    800: "expired",
    801: "waiting_scan",
    802: "waiting_confirm",
    803: "success",
}

_REPO_URL = "https://github.com/darknessomi/musicbox"

_ROOT_HELP_BANNER = f"""\
musicbox — NetEase MusicBox CLI tool.

USAGE:
    musicbox                                    # Launch curses TUI
    musicbox <command> [subcommand] [options]
    musicbox search <keyword> --type song --json
    musicbox song url <id> [--quality lossless]
    musicbox auth login --no-wait --json

EXAMPLES:
    # Search songs
    musicbox search 周杰伦 --type song --json

    # Get playable URL (pipe-friendly)
    musicbox song url 33894312 --quality lossless --quiet

    # QR login split-flow (round 1: show QR code to user)
    musicbox auth login --no-wait --json

    # QR login split-flow (round 2: after user scanned)
    musicbox auth login --check <unikey> --json

    # List charts and playlist tracks
    musicbox toplist --json
    musicbox playlist show 3778678 --json

AI AGENT SKILLS:
    musicbox pairs with AI agent skills (Cursor, Claude Code, etc.) that
    teach the agent CLI patterns, split-flow login, and error handling.

    Install the skill:
        npx skills add darknessomi/musicbox -y

    Learn more: {_REPO_URL}/tree/main/skills/musicbox

COMMUNITY:
    GitHub:     {_REPO_URL}
    Issues:     {_REPO_URL}/issues

More help: musicbox <command> --help

"""


class MusicboxArgumentParser(argparse.ArgumentParser):
    def format_help(self) -> str:
        return _ROOT_HELP_BANNER + super().format_help()


def check_latest_version() -> str | int:
    try:
        return NetEase().get_version()["info"]["version"]
    except (KeyError, TypeError):
        return 0


def print_version() -> int:
    version = __version__
    latest = check_latest_version()
    with contextlib.suppress(curses.error):
        curses.endwin()
    print("NetEase-MusicBox installed version:" + version)
    if latest and str(latest) != version:
        print("NetEase-MusicBox latest version:" + str(latest))
    return EXIT_OK


class CliContext:
    def __init__(self, json_mode: bool = False, quiet: bool = False):
        self.json_mode = json_mode
        self.quiet = quiet

    def emit_ok(
        self,
        data: Any,
        human: str,
        *,
        quiet_value: str | None = None,
        notice: dict[str, Any] | None = None,
    ) -> int:
        if self.quiet:
            if quiet_value is not None:
                print(quiet_value)
            return EXIT_OK
        if self.json_mode:
            payload: dict[str, Any] = {"ok": True, "data": data}
            if notice:
                payload["_notice"] = notice
            print(json.dumps(payload, ensure_ascii=False))
            return EXIT_OK
        print(human)
        return EXIT_OK

    def emit_err(
        self,
        error_type: str,
        message: str,
        hint: str = "",
        *,
        exit_code: int = EXIT_GENERIC,
    ) -> int:
        if self.json_mode:
            error = {"type": error_type, "message": message}
            if hint:
                error["hint"] = hint
            print(
                json.dumps({"ok": False, "error": error}, ensure_ascii=False),
                file=sys.stderr,
            )
        else:
            text = message
            if hint:
                text = f"{message}\n提示: {hint}"
            print(text, file=sys.stderr)
        return exit_code


def _update_notice() -> dict[str, Any] | None:
    try:
        latest = NetEase().get_version().get("info", {}).get("version")
        if latest and str(latest) != __version__:
            return {
                "update": {
                    "message": f"新版本 {latest} 可用",
                    "command": "pip install -U NetEase-MusicBox",
                }
            }
    except (KeyError, TypeError, AttributeError):
        pass
    return None


def _ctx_from_ns(ns: argparse.Namespace) -> CliContext:
    return CliContext(json_mode=ns.json, quiet=ns.quiet)


def _require_logged_in(api: NetEase, ctx: CliContext) -> bool:
    info = api.get_account_info()
    if info.get("account") or info.get("profile"):
        return True
    ctx.emit_err(
        "not_logged_in",
        "未登录或登录已过期",
        "musicbox auth login --no-wait --json",
        exit_code=EXIT_NOT_LOGGED_IN,
    )
    return False


def _on_login_success(api: NetEase, storage: Storage) -> dict[str, Any]:
    info = api.get_account_info()
    account = info.get("account") or {}
    profile = info.get("profile") or {}
    userid = account.get("id")
    nickname = profile.get("nickname") or ""
    storage.login(nickname, "", userid, nickname)
    storage.save()
    return {
        "user_id": userid,
        "nickname": nickname,
    }


def _render_qr_ascii(url: str) -> str:
    import qrcode

    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    buf = io.StringIO()
    qr.print_ascii(out=buf, invert=True)
    return buf.getvalue().rstrip()


def _format_song_line(song: dict[str, Any]) -> str:
    name = song.get("song_name") or song.get("name") or "?"
    artist = song.get("artist") or "?"
    sid = song.get("song_id") or song.get("id") or "?"
    return f"{sid}\t{name} — {artist}"


def _format_search_results(items: list[dict[str, Any]], search_type: str) -> str:
    lines = []
    for item in items:
        if search_type == "song":
            lines.append(_format_song_line(item))
        elif search_type == "artist":
            lines.append(
                f"{item.get('artist_id', '?')}\t{item.get('artist_name', '?')}"
            )
        elif search_type == "album":
            lines.append(
                f"{item.get('album_id', '?')}\t{item.get('album_name', '?')} "
                f"— {item.get('artist', '?')}"
            )
        elif search_type == "playlist":
            lines.append(
                f"{item.get('playlist_id', '?')}\t{item.get('playlist_name', '?')}"
            )
        else:
            lines.append(json.dumps(item, ensure_ascii=False))
    return "\n".join(lines) if lines else "(无结果)"


def cmd_search(api: NetEase, ctx: CliContext, args: argparse.Namespace) -> int:
    api_type, category = SEARCH_TYPES[args.type]
    result = api.search(args.keyword, api_type, limit=args.limit) or {}
    items = result.get(category, [])
    if args.type == "song":
        items = api.dig_info(items, "songs")
    elif args.type == "artist":
        items = api.dig_info(items, "artists")
    elif args.type == "album":
        items = api.dig_info(items, "albums")
    elif args.type == "playlist":
        items = api.dig_info(items, "playlists")
    human = _format_search_results(items, args.type)
    quiet_value = (
        str(items[0].get("song_id") or items[0].get("id", "")) if items else ""
    )
    return ctx.emit_ok(
        items,
        human,
        quiet_value=quiet_value or None,
        notice=_update_notice() if ctx.json_mode else None,
    )


def cmd_song_info(api: NetEase, ctx: CliContext, args: argparse.Namespace) -> int:
    songs = api.songs_detail([args.id])
    if not songs:
        return ctx.emit_err("api_error", f"未找到歌曲 {args.id}")
    song = songs[0]
    human = (
        f"{song.get('id')}\t{song.get('name')} — "
        f"{', '.join(a['name'] for a in song.get('ar', []))}"
    )
    return ctx.emit_ok(
        song,
        human,
        quiet_value=str(song.get("id")),
        notice=_update_notice() if ctx.json_mode else None,
    )


def cmd_song_url(api: NetEase, ctx: CliContext, args: argparse.Namespace) -> int:
    config = Config()
    old_quality = config.get("music_quality")
    if args.quality:
        config.config.setdefault("music_quality", {})["value"] = args.quality
    try:
        urls = api.songs_url([args.id])
    finally:
        if args.quality:
            config.config["music_quality"]["value"] = old_quality
    if not urls:
        return ctx.emit_err("api_error", f"无法获取歌曲 {args.id} 的播放链接")
    url_info = urls[0]
    human = url_info.get("url") or "(无链接)"
    return ctx.emit_ok(
        url_info,
        human,
        quiet_value=url_info.get("url"),
        notice=_update_notice() if ctx.json_mode else None,
    )


def cmd_playlist_show(api: NetEase, ctx: CliContext, args: argparse.Namespace) -> int:
    track_ids = api.playlist_songlist(args.id)
    if not track_ids:
        return ctx.emit_err("api_error", f"歌单 {args.id} 为空或不存在")
    songs = api.dig_info(track_ids, "songs")
    human = _format_search_results(songs, "song")
    return ctx.emit_ok(
        songs,
        human,
        notice=_update_notice() if ctx.json_mode else None,
    )


def cmd_toplist(api: NetEase, ctx: CliContext, args: argparse.Namespace) -> int:
    charts = api.fetch_toplists()
    data = [
        {"index": idx, "name": name, "id": int(chart_id)}
        for idx, (name, chart_id) in enumerate(charts)
    ]
    if args.index is not None:
        if args.index < 0 or args.index >= len(charts):
            return ctx.emit_err(
                "invalid_args",
                f"索引 {args.index} 超出范围 (0-{len(charts) - 1})",
                "musicbox toplist --help",
                exit_code=EXIT_INVALID_ARGS,
            )
        songs = api.top_songlist(args.index)
        songs = api.dig_info(songs, "songs")
        human = _format_search_results(songs, "song")
        return ctx.emit_ok(songs, human)
    human = "\n".join(f"{d['index']}\t{d['name']} ({d['id']})" for d in data)
    return ctx.emit_ok(data, human or "(无榜单)")


def cmd_recommend(api: NetEase, ctx: CliContext, args: argparse.Namespace) -> int:
    if not _require_logged_in(api, ctx):
        return EXIT_NOT_LOGGED_IN
    if args.target == "songs":
        raw = api.recommend_playlist(limit=args.limit)
        data = api.dig_info(raw, "songs")
        human = _format_search_results(data, "song")
    else:
        data = api.recommend_resource()
        human = (
            "\n".join(f"{p.get('id', '?')}\t{p.get('name', '?')}" for p in data)
            or "(无推荐歌单)"
        )
    return ctx.emit_ok(data, human)


def cmd_fm(api: NetEase, ctx: CliContext, args: argparse.Namespace) -> int:
    if not _require_logged_in(api, ctx):
        return EXIT_NOT_LOGGED_IN
    raw = api.personal_fm()
    data = api.dig_info(raw, "fmsongs")
    human = _format_search_results(data, "song")
    return ctx.emit_ok(data, human)


def cmd_comments(api: NetEase, ctx: CliContext, args: argparse.Namespace) -> int:
    result = api.song_comments(args.id, limit=args.limit)
    comments = result.get("comments", [])
    human = (
        "\n".join(
            f"{c.get('user', {}).get('nickname', '?')}: {c.get('content', '')}"
            for c in comments
        )
        or "(无评论)"
    )
    return ctx.emit_ok({"comments": comments, "total": result.get("total")}, human)


def cmd_like(api: NetEase, ctx: CliContext, args: argparse.Namespace) -> int:
    if not _require_logged_in(api, ctx):
        return EXIT_NOT_LOGGED_IN
    ok = api.song_like(args.id)
    if not ok:
        return ctx.emit_err("api_error", f"红心歌曲 {args.id} 失败")
    return ctx.emit_ok({"song_id": args.id, "liked": True}, f"已红心 {args.id}")


def cmd_auth_status(api: NetEase, ctx: CliContext, args: argparse.Namespace) -> int:
    storage = Storage()
    storage.load()
    raw_user = storage.database.get("user", {})
    user = raw_user if isinstance(raw_user, dict) else {}
    info = api.get_account_info()
    account = info.get("account") or {}
    profile = info.get("profile") or {}
    logged_in = bool(account or profile)
    data = {
        "logged_in": logged_in,
        "user_id": account.get("id") or user.get("user_id"),
        "nickname": profile.get("nickname") or user.get("nickname"),
    }
    if logged_in:
        human = f"已登录: {data['nickname']} (id={data['user_id']})"
    else:
        human = "未登录"
    return ctx.emit_ok(
        data,
        human,
        quiet_value=str(data["user_id"]) if data["user_id"] else "",
    )


def cmd_auth_login(api: NetEase, ctx: CliContext, args: argparse.Namespace) -> int:
    if args.check:
        resp = api.login_qr_check(args.check)
        code = resp.get("code")
        status = LOGIN_STATUS.get(code, "unknown")
        if code == 803:
            storage = Storage()
            storage.load()
            user = _on_login_success(api, storage)
            data = {"status": status, "code": code, **user}
            return ctx.emit_ok(data, f"登录成功: {user['nickname']}")
        data = {"status": status, "code": code, "message": resp.get("message", "")}
        human = f"登录状态: {status} (code={code})"
        return ctx.emit_ok(data, human)
    if not args.no_wait:
        return ctx.emit_err(
            "invalid_args",
            "请使用 --no-wait 发起登录，或 --check <unikey> 检查扫码结果",
            "musicbox auth login --no-wait --json",
            exit_code=EXIT_INVALID_ARGS,
        )
    unikey = api.login_qr_key()
    if not unikey:
        return ctx.emit_err("api_error", "获取登录二维码失败")
    qr_ascii = _render_qr_ascii(api.login_qr_url(unikey))
    data = {"unikey": unikey, "qr_ascii": qr_ascii}
    human = f"{qr_ascii}\n请使用网易云音乐 App 扫描二维码登录。"
    return ctx.emit_ok(
        data,
        human,
        quiet_value=unikey,
    )


def cmd_auth_logout(api: NetEase, ctx: CliContext, args: argparse.Namespace) -> int:
    if not args.yes:
        return ctx.emit_err(
            "confirmation_required",
            "登出将清除 cookie 与账号缓存，需确认后执行",
            "musicbox auth logout --yes",
            exit_code=EXIT_CONFIRM_REQUIRED,
        )
    api.logout()
    return ctx.emit_ok({"logged_out": True}, "已登出")


def _read_config_value(config: Config, key: str) -> Any:
    """Read a config value; handles bare scalars (e.g. top-level version: 9)."""
    if key not in config.config:
        if key not in config.default_config:
            raise KeyError(key)
        entry = config.default_config[key]
    else:
        entry = config.config[key]
    if isinstance(entry, dict) and "value" in entry:
        return entry["value"]
    return entry


def cmd_config_get(ctx: CliContext, args: argparse.Namespace) -> int:
    config = Config()
    try:
        value = _read_config_value(config, args.key)
    except KeyError:
        return ctx.emit_err(
            "invalid_args",
            f"未知配置项: {args.key}",
            "musicbox config list",
            exit_code=EXIT_INVALID_ARGS,
        )
    return ctx.emit_ok(
        {args.key: value}, f"{args.key} = {json.dumps(value, ensure_ascii=False)}"
    )


def cmd_config_list(ctx: CliContext, args: argparse.Namespace) -> int:
    config = Config()
    data = {key: _read_config_value(config, key) for key in config.config}
    human = "\n".join(
        f"{key} = {json.dumps(val, ensure_ascii=False)}" for key, val in data.items()
    )
    return ctx.emit_ok(data, human)


def _format_time(seconds: float | int | None) -> str:
    total = int(seconds or 0)
    return f"{total // 60:02d}:{total % 60:02d}"


_STATE_PREFIX = {"playing": "▶", "paused": "⏸", "stopped": "■"}


def _format_status(data: dict[str, Any]) -> str:
    state = data.get("state", "stopped")
    prefix = _STATE_PREFIX.get(state, "?")
    song = data.get("song") or {}
    if not song.get("name"):
        return f"{prefix} {state}  (空队列)  vol {data.get('volume')}"
    pos = _format_time(data.get("position"))
    length = _format_time(data.get("length"))
    return (
        f"{prefix} {state}  {song.get('name')} — {song.get('artist')} "
        f"[{pos} / {length}]  vol {data.get('volume')}  "
        f"mode {data.get('mode')}"
    )


def _ensure_daemon(ctx: CliContext, ns: argparse.Namespace) -> int | None:
    """Make sure a daemon is reachable. Returns an exit code on failure."""
    if is_daemon_running():
        return None
    if getattr(ns, "no_daemon_autostart", False):
        return ctx.emit_err(
            "daemon_not_running",
            "daemon 未运行，且已禁用自动启动",
            "musicbox daemon start",
            exit_code=EXIT_DAEMON_NOT_RUNNING,
        )
    if not spawn_daemon():
        return ctx.emit_err(
            "daemon_not_running",
            "daemon 自动启动失败",
            "musicbox daemon start",
            exit_code=EXIT_DAEMON_NOT_RUNNING,
        )
    return None


def _rpc(
    ctx: CliContext,
    ns: argparse.Namespace,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    human_fn: Any = None,
    quiet_value: Any = None,
) -> int:
    """Dispatch a control command to the daemon, mapping responses to CLI I/O."""
    params = params or {}
    if getattr(ns, "dry_run", False):
        preview = {"method": method, "params": params}
        return ctx.emit_ok(preview, f"[dry-run] {method} {json.dumps(params)}")

    failed = _ensure_daemon(ctx, ns)
    if failed is not None:
        return failed

    try:
        resp = send_request(method, params)
    except ConnectionError:
        return ctx.emit_err(
            "daemon_not_running",
            "无法连接 daemon",
            "musicbox daemon start",
            exit_code=EXIT_DAEMON_NOT_RUNNING,
        )
    except (OSError, ValueError) as exc:
        return ctx.emit_err("api_error", f"daemon 通信失败: {exc}")

    if resp.get("ok"):
        data = resp.get("data")
        human = human_fn(data) if human_fn else json.dumps(data, ensure_ascii=False)
        qv = quiet_value(data) if callable(quiet_value) else quiet_value
        return ctx.emit_ok(data, human, quiet_value=qv)

    error = resp.get("error") or {}
    return ctx.emit_err(
        error.get("type", "api_error"),
        error.get("message", "daemon 返回错误"),
        error.get("hint", ""),
        exit_code=_ERROR_EXIT_CODES.get(error.get("type", ""), EXIT_GENERIC),
    )


def cmd_play(ctx: CliContext, ns: argparse.Namespace) -> int:
    params: dict[str, Any] = {}
    if ns.id is not None:
        params["id"] = ns.id
    if ns.playlist is not None:
        params["playlist"] = ns.playlist
    if ns.index is not None:
        params["index"] = ns.index
    return _rpc(ctx, ns, "player.play", params, human_fn=_format_status)


def cmd_simple_control(ctx: CliContext, ns: argparse.Namespace, method: str) -> int:
    return _rpc(ctx, ns, method, human_fn=_format_status)


def cmd_next(ctx: CliContext, ns: argparse.Namespace) -> int:
    return _rpc(ctx, ns, "player.next", {"n": ns.n}, human_fn=_format_status)


def cmd_prev(ctx: CliContext, ns: argparse.Namespace) -> int:
    return _rpc(ctx, ns, "player.prev", {"n": ns.n}, human_fn=_format_status)


def cmd_volume(ctx: CliContext, ns: argparse.Namespace) -> int:
    spec = ns.value
    params: dict[str, Any]
    if spec.startswith("+") or spec.startswith("-"):
        try:
            params = {"delta": int(spec)}
        except ValueError:
            return ctx.emit_err(
                "invalid_args",
                f"无效音量增量: {spec}",
                "musicbox volume +10 | -10 | 50",
                exit_code=EXIT_INVALID_ARGS,
            )
    else:
        try:
            params = {"value": int(spec)}
        except ValueError:
            return ctx.emit_err(
                "invalid_args",
                f"无效音量值: {spec}",
                "musicbox volume 50",
                exit_code=EXIT_INVALID_ARGS,
            )
    return _rpc(ctx, ns, "player.volume", params, human_fn=_format_status)


def cmd_mode(ctx: CliContext, ns: argparse.Namespace) -> int:
    return _rpc(ctx, ns, "player.mode", {"mode": ns.mode}, human_fn=_format_status)


def cmd_seek(ctx: CliContext, ns: argparse.Namespace) -> int:
    spec = ns.position
    relative = spec.startswith("+") or spec.startswith("-")
    try:
        seconds = int(spec)
    except ValueError:
        return ctx.emit_err(
            "invalid_args",
            f"无效 seek 值: {spec}",
            "musicbox seek 90 | +15 | -15",
            exit_code=EXIT_INVALID_ARGS,
        )
    return _rpc(
        ctx,
        ns,
        "player.seek",
        {"seconds": seconds, "relative": relative},
        human_fn=_format_status,
    )


def cmd_status(ctx: CliContext, ns: argparse.Namespace) -> int:
    return _rpc(ctx, ns, "player.status", human_fn=_format_status)


def cmd_lyrics(ctx: CliContext, ns: argparse.Namespace) -> int:
    def human(data: dict[str, Any]) -> str:
        lines = data.get("lyric") or []
        return "\n".join(lines) if lines else "(无歌词)"

    return _rpc(ctx, ns, "player.lyrics", {"current": True}, human_fn=human)


def _format_queue(data: dict[str, Any]) -> str:
    items = data.get("items") or []
    if not items:
        return "(队列为空)"
    lines = []
    for item in items:
        marker = "▶" if item.get("current") else " "
        lines.append(
            f"{marker} {item['index']}\t{item.get('song_id')}\t"
            f"{item.get('name')} — {item.get('artist')}"
        )
    return "\n".join(lines)


def cmd_queue_list(ctx: CliContext, ns: argparse.Namespace) -> int:
    return _rpc(ctx, ns, "queue.list", human_fn=_format_queue)


def cmd_queue_add(ctx: CliContext, ns: argparse.Namespace) -> int:
    return _rpc(ctx, ns, "queue.add", {"ids": ns.ids}, human_fn=_format_queue)


def cmd_queue_play(ctx: CliContext, ns: argparse.Namespace) -> int:
    return _rpc(ctx, ns, "queue.play", {"index": ns.index}, human_fn=_format_status)


def cmd_queue_clear(ctx: CliContext, ns: argparse.Namespace) -> int:
    if not ns.yes:
        return ctx.emit_err(
            "confirmation_required",
            "清空播放队列将丢弃当前队列，需确认后执行",
            "musicbox queue clear --yes",
            exit_code=EXIT_CONFIRM_REQUIRED,
        )
    return _rpc(ctx, ns, "queue.clear", human_fn=_format_queue)


def cmd_daemon(ctx: CliContext, ns: argparse.Namespace) -> int:
    action = ns.action
    if action == "status":
        running = is_daemon_running()
        data: dict[str, Any] = {"running": running}
        if running:
            try:
                resp = send_request("daemon.ping")
                if resp.get("ok"):
                    data["pid"] = resp["data"].get("pid")
            except (ConnectionError, OSError, ValueError):
                pass
        return ctx.emit_ok(
            data,
            "daemon 正在运行" + (f" (pid={data['pid']})" if data.get("pid") else "")
            if running
            else "daemon 未运行",
            quiet_value="running" if running else "stopped",
        )
    if action == "start":
        if is_daemon_running():
            return ctx.emit_ok({"running": True, "started": False}, "daemon 已在运行")
        if spawn_daemon():
            return ctx.emit_ok({"running": True, "started": True}, "daemon 已启动")
        return ctx.emit_err("api_error", "daemon 启动失败")
    if action == "stop":
        if stop_daemon():
            return ctx.emit_ok({"running": False, "stopped": True}, "daemon 已停止")
        return ctx.emit_ok({"running": False, "stopped": False}, "daemon 未运行")
    if action == "restart":
        stop_daemon()
        if spawn_daemon():
            return ctx.emit_ok({"running": True}, "daemon 已重启")
        return ctx.emit_err("api_error", "daemon 重启失败")
    return ctx.emit_err("invalid_args", f"未知 daemon 动作: {action}")


def _add_control_flags(parser: argparse.ArgumentParser) -> None:
    _add_common_flags(parser)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将发送的 RPC 请求，不产生副作用",
    )
    parser.add_argument(
        "--no-daemon-autostart",
        action="store_true",
        help="禁止自动拉起 daemon（不在跑则返回 exit 4）",
    )


def _add_common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出结构化 JSON 信封",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="仅输出关键值（便于管道取值）",
    )


def _build_parser() -> MusicboxArgumentParser:
    parser = MusicboxArgumentParser(
        prog="musicbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="显示版本并退出",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # search
    p_search = sub.add_parser(
        "search",
        help="搜索歌曲/歌手/专辑/歌单/电台",
        description="搜索网易云音乐资源",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  musicbox search 周杰伦 --type song --json\n"
            "  musicbox search 范特西 --type album --limit 5"
        ),
    )
    _add_common_flags(p_search)
    p_search.add_argument("keyword", help="搜索关键词")
    p_search.add_argument(
        "--type",
        choices=list(SEARCH_TYPES),
        default="song",
        help="搜索类型 (默认: song)",
    )
    p_search.add_argument("--limit", type=int, default=20, help="返回条数上限")
    p_search.set_defaults(handler="search")

    # song
    p_song = sub.add_parser("song", help="歌曲信息与播放链接")
    song_sub = p_song.add_subparsers(dest="song_cmd", metavar="SUBCOMMAND")

    p_song_info = song_sub.add_parser(
        "info",
        help="歌曲详情",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox song info 33894312 --json",
    )
    _add_common_flags(p_song_info)
    p_song_info.add_argument("id", type=int, help="歌曲 ID")
    p_song_info.set_defaults(handler="song_info")

    p_song_url = song_sub.add_parser(
        "url",
        help="歌曲播放链接",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  musicbox song url 33894312 --json\n"
            "  musicbox song url 33894312 --quality lossless --quiet"
        ),
    )
    _add_common_flags(p_song_url)
    p_song_url.add_argument("id", type=int, help="歌曲 ID")
    p_song_url.add_argument(
        "--quality",
        default="",
        help="音质: standard|higher|exhigh|lossless|hires 等",
    )
    p_song_url.set_defaults(handler="song_url")

    # playlist
    p_playlist = sub.add_parser("playlist", help="歌单操作")
    playlist_sub = p_playlist.add_subparsers(dest="playlist_cmd")

    p_playlist_show = playlist_sub.add_parser(
        "show",
        help="查看歌单歌曲列表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox playlist show 3778678 --json",
    )
    _add_common_flags(p_playlist_show)
    p_playlist_show.add_argument("id", type=int, help="歌单 ID")
    p_playlist_show.set_defaults(handler="playlist_show")

    # toplist
    p_toplist = sub.add_parser(
        "toplist",
        help="排行榜列表或指定榜单歌曲",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n  musicbox toplist --json\n  musicbox toplist --index 0 --json"
        ),
    )
    _add_common_flags(p_toplist)
    p_toplist.add_argument(
        "--index",
        type=int,
        default=None,
        help="榜单索引，指定后返回该榜歌曲",
    )
    p_toplist.set_defaults(handler="toplist")

    # recommend
    p_recommend = sub.add_parser(
        "recommend",
        help="每日推荐（需登录）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  musicbox recommend songs --json\n"
            "  musicbox recommend playlists --json"
        ),
    )
    _add_common_flags(p_recommend)
    p_recommend.add_argument(
        "target",
        choices=["songs", "playlists"],
        help="推荐类型",
    )
    p_recommend.add_argument("--limit", type=int, default=20)
    p_recommend.set_defaults(handler="recommend")

    # fm
    p_fm = sub.add_parser(
        "fm",
        help="私人 FM 一批歌曲（需登录）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox fm --json",
    )
    _add_common_flags(p_fm)
    p_fm.set_defaults(handler="fm")

    # comments
    p_comments = sub.add_parser(
        "comments",
        help="歌曲评论",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox comments 33894312 --limit 10 --json",
    )
    _add_common_flags(p_comments)
    p_comments.add_argument("id", type=int, help="歌曲 ID")
    p_comments.add_argument("--limit", type=int, default=20)
    p_comments.set_defaults(handler="comments")

    # like
    p_like = sub.add_parser(
        "like",
        help="红心歌曲（需登录，加入「我喜欢」）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox like 33894312 --json",
    )
    _add_common_flags(p_like)
    p_like.add_argument("id", type=int, help="歌曲 ID")
    p_like.set_defaults(handler="like")

    # auth
    p_auth = sub.add_parser("auth", help="登录与身份")
    auth_sub = p_auth.add_subparsers(dest="auth_cmd")

    p_auth_status = auth_sub.add_parser(
        "status",
        help="当前登录状态",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox auth status --json",
    )
    _add_common_flags(p_auth_status)
    p_auth_status.set_defaults(handler="auth_status")

    p_auth_login = auth_sub.add_parser(
        "login",
        help="扫码登录（split-flow）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  musicbox auth login --no-wait --json\n"
            "  musicbox auth login --check <unikey> --json"
        ),
    )
    _add_common_flags(p_auth_login)
    p_auth_login.add_argument(
        "--no-wait",
        action="store_true",
        help="立即输出登录二维码和 unikey，不阻塞轮询",
    )
    p_auth_login.add_argument(
        "--check",
        metavar="UNIKEY",
        default="",
        help="检查扫码结果（下一轮 Agent 调用）",
    )
    p_auth_login.set_defaults(handler="auth_login")

    p_auth_logout = auth_sub.add_parser(
        "logout",
        help="登出（高风险，需 --yes）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox auth logout --yes",
    )
    _add_common_flags(p_auth_logout)
    p_auth_logout.add_argument(
        "--yes",
        action="store_true",
        help="确认执行登出",
    )
    p_auth_logout.set_defaults(handler="auth_logout")

    # config
    p_config = sub.add_parser("config", help="读取配置")
    config_sub = p_config.add_subparsers(dest="config_cmd")

    p_config_get = config_sub.add_parser(
        "get",
        help="读取单项配置",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox config get music_quality --json",
    )
    _add_common_flags(p_config_get)
    p_config_get.add_argument("key", help="配置键名")
    p_config_get.set_defaults(handler="config_get")

    p_config_list = config_sub.add_parser(
        "list",
        help="列出全部配置",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox config list --json",
    )
    _add_common_flags(p_config_list)
    p_config_list.set_defaults(handler="config_list")

    _build_control_parsers(sub)

    return parser


def _build_control_parsers(sub: Any) -> None:
    # play
    p_play = sub.add_parser(
        "play",
        help="播放歌曲/歌单，或恢复当前播放（经 daemon）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  musicbox play --id 33894312 --json\n"
            "  musicbox play --playlist 3778678\n"
            "  musicbox play              # 恢复/开始当前队列\n"
            "  musicbox play --index 3"
        ),
    )
    _add_control_flags(p_play)
    p_play.add_argument("--id", type=int, default=None, help="按歌曲 ID 播放")
    p_play.add_argument("--playlist", type=int, default=None, help="按歌单 ID 播放")
    p_play.add_argument("--index", type=int, default=None, help="播放队列中第 n 首")
    p_play.set_defaults(handler="play")

    # simple controls
    simple = {
        "pause": ("暂停", "player.pause"),
        "resume": ("继续播放", "player.resume"),
        "toggle": ("播放/暂停切换", "player.toggle"),
        "stop": ("停止播放", "player.stop"),
    }
    for name, (desc, _method) in simple.items():
        p = sub.add_parser(
            name,
            help=f"{desc}（经 daemon）",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=f"Examples:\n  musicbox {name} --json",
        )
        _add_control_flags(p)
        p.set_defaults(handler=name)

    # next / prev
    p_next = sub.add_parser(
        "next",
        help="下一曲（经 daemon）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox next\n  musicbox next 3 --json",
    )
    _add_control_flags(p_next)
    p_next.add_argument("n", type=int, nargs="?", default=1, help="向后跳 n 首")
    p_next.set_defaults(handler="next")

    p_prev = sub.add_parser(
        "prev",
        help="上一曲（经 daemon）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox prev\n  musicbox prev 2 --json",
    )
    _add_control_flags(p_prev)
    p_prev.add_argument("n", type=int, nargs="?", default=1, help="向前跳 n 首")
    p_prev.set_defaults(handler="prev")

    # volume
    p_volume = sub.add_parser(
        "volume",
        help="设置音量 0-100 或相对增减（经 daemon）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  musicbox volume 50\n"
            "  musicbox volume +10\n"
            "  musicbox volume -10 --json"
        ),
    )
    _add_control_flags(p_volume)
    p_volume.add_argument("value", help="目标音量(0-100) 或 +n / -n")
    p_volume.set_defaults(handler="volume")

    # mode
    p_mode = sub.add_parser(
        "mode",
        help="设置播放模式（经 daemon）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox mode random-loop --json",
    )
    _add_control_flags(p_mode)
    p_mode.add_argument("mode", choices=MODE_CHOICES, help="播放模式")
    p_mode.set_defaults(handler="mode")

    # seek
    p_seek = sub.add_parser(
        "seek",
        help="跳转到指定秒或相对增减（仅 mpv 后端）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n  musicbox seek 90\n  musicbox seek +15\n  musicbox seek -15"
        ),
    )
    _add_control_flags(p_seek)
    p_seek.add_argument("position", help="目标秒数，或 +n / -n 相对跳转")
    p_seek.set_defaults(handler="seek")

    # status
    p_status = sub.add_parser(
        "status",
        help="当前播放状态（Agent 的眼睛）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox status --json",
    )
    _add_control_flags(p_status)
    p_status.set_defaults(handler="status")

    # lyrics
    p_lyrics = sub.add_parser(
        "lyrics",
        help="当前歌曲歌词",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox lyrics --current --json",
    )
    _add_control_flags(p_lyrics)
    p_lyrics.add_argument(
        "--current", action="store_true", help="当前播放歌曲（默认即当前）"
    )
    p_lyrics.set_defaults(handler="lyrics")

    # queue
    p_queue = sub.add_parser("queue", help="播放队列操作（经 daemon）")
    queue_sub = p_queue.add_subparsers(dest="queue_cmd")

    p_queue_list = queue_sub.add_parser(
        "list",
        help="查看播放队列",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox queue list --json",
    )
    _add_control_flags(p_queue_list)
    p_queue_list.set_defaults(handler="queue_list")

    p_queue_add = queue_sub.add_parser(
        "add",
        help="把歌曲加入队列",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox queue add 33894312 28258988 --json",
    )
    _add_control_flags(p_queue_add)
    p_queue_add.add_argument("ids", type=int, nargs="+", help="一个或多个歌曲 ID")
    p_queue_add.set_defaults(handler="queue_add")

    p_queue_play = queue_sub.add_parser(
        "play",
        help="播放队列中第 n 首",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox queue play 2 --json",
    )
    _add_control_flags(p_queue_play)
    p_queue_play.add_argument("index", type=int, help="队列索引")
    p_queue_play.set_defaults(handler="queue_play")

    p_queue_clear = queue_sub.add_parser(
        "clear",
        help="清空播放队列（高风险，需 --yes）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  musicbox queue clear --yes",
    )
    _add_control_flags(p_queue_clear)
    p_queue_clear.add_argument("--yes", action="store_true", help="确认清空")
    p_queue_clear.set_defaults(handler="queue_clear")

    # daemon
    p_daemon = sub.add_parser(
        "daemon",
        help="守护进程生命周期管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  musicbox daemon start\n"
            "  musicbox daemon status --json\n"
            "  musicbox daemon stop\n"
            "  musicbox daemon restart"
        ),
    )
    _add_common_flags(p_daemon)
    p_daemon.add_argument(
        "action",
        choices=["start", "stop", "status", "restart"],
        help="守护进程动作",
    )
    p_daemon.set_defaults(handler="daemon")


def dispatch(api: NetEase, ns: argparse.Namespace) -> int:
    ctx = _ctx_from_ns(ns)
    handler = getattr(ns, "handler", None)
    if not handler:
        return ctx.emit_err(
            "invalid_args",
            "缺少子命令",
            "musicbox <command> --help",
            exit_code=EXIT_INVALID_ARGS,
        )

    handlers: dict[str, Any] = {
        "search": lambda: cmd_search(api, ctx, ns),
        "song_info": lambda: cmd_song_info(api, ctx, ns),
        "song_url": lambda: cmd_song_url(api, ctx, ns),
        "playlist_show": lambda: cmd_playlist_show(api, ctx, ns),
        "toplist": lambda: cmd_toplist(api, ctx, ns),
        "recommend": lambda: cmd_recommend(api, ctx, ns),
        "fm": lambda: cmd_fm(api, ctx, ns),
        "comments": lambda: cmd_comments(api, ctx, ns),
        "like": lambda: cmd_like(api, ctx, ns),
        "auth_status": lambda: cmd_auth_status(api, ctx, ns),
        "auth_login": lambda: cmd_auth_login(api, ctx, ns),
        "auth_logout": lambda: cmd_auth_logout(api, ctx, ns),
        "config_get": lambda: cmd_config_get(ctx, ns),
        "config_list": lambda: cmd_config_list(ctx, ns),
        "play": lambda: cmd_play(ctx, ns),
        "pause": lambda: cmd_simple_control(ctx, ns, "player.pause"),
        "resume": lambda: cmd_simple_control(ctx, ns, "player.resume"),
        "toggle": lambda: cmd_simple_control(ctx, ns, "player.toggle"),
        "stop": lambda: cmd_simple_control(ctx, ns, "player.stop"),
        "next": lambda: cmd_next(ctx, ns),
        "prev": lambda: cmd_prev(ctx, ns),
        "volume": lambda: cmd_volume(ctx, ns),
        "mode": lambda: cmd_mode(ctx, ns),
        "seek": lambda: cmd_seek(ctx, ns),
        "status": lambda: cmd_status(ctx, ns),
        "lyrics": lambda: cmd_lyrics(ctx, ns),
        "queue_list": lambda: cmd_queue_list(ctx, ns),
        "queue_add": lambda: cmd_queue_add(ctx, ns),
        "queue_play": lambda: cmd_queue_play(ctx, ns),
        "queue_clear": lambda: cmd_queue_clear(ctx, ns),
        "daemon": lambda: cmd_daemon(ctx, ns),
    }
    fn = handlers.get(handler)
    if not fn:
        return ctx.emit_err(
            "invalid_args",
            f"未知命令: {handler}",
            exit_code=EXIT_INVALID_ARGS,
        )
    return fn()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code is None:
            return EXIT_INVALID_ARGS
        return int(exc.code)

    if ns.version:
        return print_version()

    if not getattr(ns, "command", None):
        parser.print_help()
        return EXIT_INVALID_ARGS

    # Nested subcommands without handler
    if ns.command == "song" and not getattr(ns, "handler", None):
        parser.parse_args([*argv, "--help"] if argv else ["--help"])
        return EXIT_INVALID_ARGS
    if ns.command == "playlist" and not getattr(ns, "handler", None):
        parser.parse_args([*argv, "--help"] if argv else ["--help"])
        return EXIT_INVALID_ARGS
    if ns.command == "auth" and not getattr(ns, "handler", None):
        parser.parse_args([*argv, "--help"] if argv else ["--help"])
        return EXIT_INVALID_ARGS
    if ns.command == "config" and not getattr(ns, "handler", None):
        parser.parse_args([*argv, "--help"] if argv else ["--help"])
        return EXIT_INVALID_ARGS
    if ns.command == "queue" and not getattr(ns, "handler", None):
        parser.parse_args([*argv, "--help"] if argv else ["--help"])
        return EXIT_INVALID_ARGS

    api = NetEase()
    return dispatch(api, ns)
