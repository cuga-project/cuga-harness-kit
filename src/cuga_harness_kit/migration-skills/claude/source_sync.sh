#!/usr/bin/env bash
# Scout a source repo and write a CLAUDE.md to guide the analyst.
# Run this before migrate.sh when adding a new source repo, or to refresh an existing CLAUDE.md.
#
# Usage: ./source_sync.sh <source-name>
#        ./source_sync.sh cp4i-res

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Colours ────────────────────────────────────────────────────────────────────
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
DIM='\033[2m'
NC='\033[0m'

# ── Header ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║       CUGA Source Sync            ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════╝${NC}"
echo ""

# ── Environment variables ──────────────────────────────────────────────────────
# Load credentials from .env (gitignored). Shell env vars take precedence.
ENV_FILE="$REPO/.env"
if [[ -f "$ENV_FILE" ]]; then
    set -o allexport
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +o allexport
    echo -e "${DIM}Loaded credentials from .env${NC}"
else
    echo -e "${YELLOW}⚠  No .env file found at $ENV_FILE${NC}"
    echo "   Copy .env.example to .env and fill in your credentials."
    echo ""
fi

# Validate required vars
MISSING=()
[[ -z "${ANTHROPIC_AUTH_TOKEN:-}" ]] && MISSING+=("ANTHROPIC_AUTH_TOKEN")
[[ -z "${ANTHROPIC_MODEL:-}"      ]] && MISSING+=("ANTHROPIC_MODEL")
if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo -e "${RED}✗ Missing required environment variables: ${MISSING[*]}${NC}"
    echo "  Set them in .env or export them before running this script."
    exit 1
fi

export ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL:-}"
export ANTHROPIC_AUTH_TOKEN
export ANTHROPIC_MODEL
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS="${CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS:-1}"

mkdir -p "$REPO/.claude"
cat > "$REPO/.claude/settings.local.json" <<EOF
{
  "model": "$ANTHROPIC_MODEL",
  "env": {
    "ANTHROPIC_BASE_URL": "$ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN": "$ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_MODEL": "$ANTHROPIC_MODEL",
    "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "$CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS"
  }
}
EOF
echo -e "${DIM}Settings written → .claude/settings.local.json${NC}"

# ── Preflight checks ───────────────────────────────────────────────────────────
if ! command -v claude &>/dev/null; then
    echo -e "${RED}✗ claude not found.${NC}"
    echo "  Install Claude Code: https://claude.ai/code"
    exit 1
fi

# ── Source name ────────────────────────────────────────────────────────────────
SOURCE_NAME="${1:-}"

if [[ -z "$SOURCE_NAME" ]]; then
    echo -e "${BOLD}Available sources in migration_from/:${NC}"
    if ls "$REPO/migration_from/" &>/dev/null && [[ -n "$(ls -A "$REPO/migration_from/")" ]]; then
        ls "$REPO/migration_from/" | sed "s/^/  ${DIM}•${NC} /"
    else
        echo -e "  ${DIM}(none — add a source repo under migration_from/)${NC}"
    fi
    echo ""
    read -rp "  Source name: " SOURCE_NAME
fi

SOURCE_PATH="$REPO/migration_from/$SOURCE_NAME"
if [[ ! -d "$SOURCE_PATH" ]]; then
    echo -e "${RED}✗ Source not found: migration_from/$SOURCE_NAME${NC}"
    exit 1
fi

CLAUDE_MD="$SOURCE_PATH/CLAUDE.md"
if [[ -f "$CLAUDE_MD" ]]; then
    echo -e "${YELLOW}ℹ  CLAUDE.md already exists at migration_from/$SOURCE_NAME/CLAUDE.md${NC}"
    echo "   The agent will update it rather than overwrite."
    echo ""
fi

echo -e "${BOLD}Source sync plan:${NC}"
echo -e "  Source   ${CYAN}migration_from/$SOURCE_NAME${NC}"
echo -e "  Output   ${CYAN}migration_from/$SOURCE_NAME/CLAUDE.md${NC}"
echo ""

# ── Dispatch background session ────────────────────────────────────────────────
echo -e "${BOLD}Dispatching sync session…${NC}"
cd "$REPO"

SESSION_NAME="source-sync → $SOURCE_NAME"
claude --bg "/source_sync $SOURCE_NAME" --name "$SESSION_NAME" 2>/dev/null || {
    PROMPT="You are the Source Sync Agent. Follow the instructions in .claude/commands/source_sync.md. Source name: $SOURCE_NAME. The repo root is $REPO."
    claude --bg "$PROMPT" --name "$SESSION_NAME"
}

# ── Quit mechanism ─────────────────────────────────────────────────────────────
_CLEANUP_DONE=0
cleanup() {
    [[ "$_CLEANUP_DONE" -eq 1 ]] && return
    _CLEANUP_DONE=1
    echo ""
    echo -e "${YELLOW}Stopping sync session…${NC}"
    claude daemon stop --any 2>/dev/null || true
    echo -e "${DIM}Session stopped.${NC}"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

echo ""
echo -e "${GREEN}✓ Session dispatched: ${BOLD}$SESSION_NAME${NC}"
echo ""
echo -e "${DIM}Controls in Agent View:${NC}"
echo -e "  ${CYAN}Space${NC}   peek at current output"
echo -e "  ${CYAN}Enter${NC}   attach to the session"
echo -e "  ${CYAN}←${NC}       detach back to Agent View"
echo -e "  ${CYAN}Ctrl+C${NC}  stop the session and exit"
echo ""

# ── Open Agent View ────────────────────────────────────────────────────────────
echo -e "${BOLD}Opening Agent View…${NC}"
echo ""
claude agents --cwd "$REPO"
