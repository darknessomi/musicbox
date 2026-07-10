# AGENTS.md

## Cursor Cloud specific instructions

NetEase-MusicBox is a Python 3.10+ command-line/curses TUI music player, managed with
[`uv`](https://docs.astral.sh/uv/). There is a single package (`NEMbox`) and one product
(the `musicbox` CLI/TUI). Dependencies are refreshed automatically by the startup update
script (`uv sync --frozen`); you do not need to reinstall them.

### Running the app
- Interactive TUI: `uv run musicbox` — this uses `curses` and requires a real interactive
  terminal (TTY). It will not render in a non-TTY/headless shell; use the CLI subcommands
  below for scripted/agent verification instead.
- Agent/CLI mode (no TTY needed): `uv run musicbox <command>`, e.g.
  `search`, `song url`, `play`, `pause`, `status`, `queue`, `daemon`, `auth`.
  Add `--json` for machine-readable output. See `README.md` for the full command list.
- Playback runs through a background daemon; `musicbox play --id <id>` auto-starts it and
  `musicbox daemon stop` stops it.

### Audio backends (system deps, NOT in update script)
- `mpg123` (MP3) and `mpv` (FLAC / Hi-Res) are OS packages installed via `apt-get`
  (`sudo apt-get install -y mpg123 mpv`). They are pre-installed in the snapshot; reinstall
  only if `musicbox play` reports a missing backend. Playback selects `mpg123` by default.

### Network / API note
- Song search and playable URLs come from NetEase's public API, which only accepts
  China-region access. From other regions requests can fail or return empty; set an HTTP
  proxy (see README "配置") if search stops returning results. In this environment the API
  was reachable and returned live results.
- Login is QR-code scan only (renders a QR block in the terminal); there is no
  username/password login and no test-login secret is required for search/playback.

### Lint / test / build
Standard commands (already documented in `.cursor/rules/pre-commit-validation.mdc` and
`.github/workflows/ci.yml`); run them via `uv run`:
- `uv run ruff check`
- `uv run ruff format --check`
- `uv run ty check` — emits ~11 diagnostics that are configured as `warn` in
  `pyproject.toml`; it exits 0 and is not a failure.
- `uv run pytest -q --tb=short`
- `uv build`
