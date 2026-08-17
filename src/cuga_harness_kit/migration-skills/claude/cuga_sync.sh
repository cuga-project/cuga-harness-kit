#!/usr/bin/env bash
# Run this after updating migration_to/cuga-agent/ to a new SDK version.
# Reads the SDK source and updates templates so future /migrate runs produce accurate specs.
#
# Usage: ./cuga_sync.sh

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
echo -e "${BOLD}${CYAN}║       CUGA Template Sync          ║${NC}"
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

if [[ ! -d "$REPO/migration_to/cuga-agent" ]]; then
    echo -e "${RED}✗ cuga-agent/ not found at $REPO/migration_to/cuga-agent${NC}"
    echo "  Copy the CUGA SDK repo into migration_to/:"
    echo "    cp -r /path/to/cuga-agent $REPO/migration_to/cuga-agent"
    exit 1
fi

mkdir -p "$REPO/.cuga-migrator"

# ── Dispatch background session ────────────────────────────────────────────────
echo -e "${BOLD}Dispatching sync session…${NC}"
cd "$REPO"

SESSION_NAME="cuga-sync"
claude --bg "/cuga_sync" --name "$SESSION_NAME" 2>/dev/null || {
    PROMPT="You are the CUGA Template Sync Agent. Follow the instructions in .claude/commands/cuga_sync.md. The repo root is $REPO."
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
