#!/usr/bin/env bash
# Batch-close stale musicbox issues.
# Requires: gh auth with issues:write on darknessomi/musicbox
#
# Rules applied:
# - Keep all enhancement-labeled issues
# - Do not close issues where the bug still exists
# - Close only issues with confirmed resolution in comments
#
# Usage:
#   ./scripts/close-stale-issues.sh --dry-run
#   ./scripts/close-stale-issues.sh

set -euo pipefail

REPO="${REPO:-darknessomi/musicbox}"
DRY_RUN=false
SLEEP="${SLEEP:-1}"

COMMENT_RESOLVED='该 issue 已在讨论中解答或确认处理，长期无后续，先行关闭。如问题仍存在，请在新版本中重新提交并附上环境信息。'
COMMENT_NOTPLANNED='经讨论确认不在项目支持范围内或暂不计划处理，先行关闭。'
COMMENT_WONTFIX='该 issue 已标记 wontfix，长期无后续，先行关闭。'

usage() {
  cat <<'EOF'
Usage: close-stale-issues.sh [--dry-run] [--repo OWNER/REPO]

Closes 15 issues confirmed safe to close after comment review.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true ;;
    --repo) REPO="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
  shift
done

close_issue() {
  local num=$1 reason=$2 comment=$3 duplicate_of=${4:-}

  echo "#${num}  reason=${reason}"
  if $DRY_RUN; then
    echo "  [dry-run] gh issue close ${num} ..."
    return 0
  fi

  if [[ -n "$duplicate_of" ]]; then
    gh issue close "$num" -R "$REPO" --duplicate-of "$duplicate_of" --comment "$comment"
  else
    gh issue close "$num" -R "$REPO" --reason "$reason" --comment "$comment"
  fi
  sleep "$SLEEP"
}

echo "Repository: ${REPO}"
echo "Mode: $( $DRY_RUN && echo dry-run || echo execute )"
echo

# Tier 1: high-confidence (10)
close_issue 347 "not planned" "$COMMENT_WONTFIX"
close_issue 569 "completed" "$COMMENT_RESOLVED"
close_issue 614 "completed" "$COMMENT_RESOLVED"
close_issue 617 "completed" "$COMMENT_RESOLVED"
close_issue 689 "completed" "$COMMENT_RESOLVED"
close_issue 732 "not planned" "旧版 0.2.4.3 可回滚使用，讨论已结束，先行关闭。"
close_issue 754 "duplicate" "与 #767 重复，先行关闭。" 767
close_issue 811 "completed" "版权问题已在 #791 主分支修复，先行关闭。"
close_issue 851 "not planned" "$COMMENT_NOTPLANNED"
close_issue 918 "completed" "$COMMENT_RESOLVED"

# Tier 2: manual review, confirmed safe (5)
close_issue 726 "completed" "$COMMENT_RESOLVED"
close_issue 782 "completed" "版权问题参见 #791，先行关闭。"
close_issue 839 "completed" "$COMMENT_RESOLVED"
close_issue 747 "not planned" "MusicBox 为命令行客户端，不支持 Windows 原生运行，先行关闭。"
close_issue 904 "not planned" "MusicBox 不支持 Windows 原生运行，先行关闭。"
close_issue 911 "not planned" "Windows 因 curses/终端 signal 等限制暂不支持，先行关闭。"

echo
echo "Done. Closed (or dry-run) 15 issues."
