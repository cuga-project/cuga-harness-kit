#!/usr/bin/env bash
# Scout a source repo and write a CLAUDE.md to guide the analyst stage.
# Run this before migrate.sh when adding a new source repo, or to refresh an
# existing CLAUDE.md.
#
# Usage: ./source_sync.sh <source-name>
#        ./source_sync.sh cp4i-res
#
# See migrate.sh for notes on what this port of the launcher does NOT attempt
# (background dispatch / Agent View, an explicit skill-selection flag).
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
echo -e "${BOLD}${CYAN}║   CUGA Source Sync (Bob)          ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════╝${NC}"
echo ""

# ── Environment variables ──────────────────────────────────────────────────────
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

if [[ -z "${BOBSHELL_API_KEY:-}" ]]; then
    echo -e "${RED}✗ Missing required environment variable: BOBSHELL_API_KEY${NC}"
    echo "  Set it in .env or export it before running this script."
    exit 1
fi
export BOBSHELL_API_KEY

# ── Preflight checks ───────────────────────────────────────────────────────────
if ! command -v bob &>/dev/null; then
    echo -e "${RED}✗ bob not found.${NC}"
    echo "  Install Bob Shell — see https://bob.ibm.com/docs/shell/getting-started/install-and-setup"
    exit 1
fi

# In non-interactive mode, Bob silently overrides --yolo for folders that were
# never trusted in an interactive session — it falls back to a read-only safe
# mode (no files written, no skill activated), and this script's whole point is
# defeated without any error. This is a heuristic (checks for this exact path in
# the trust store; "trust parent folder" won't match it even though it's still
# effectively trusted), so it's a warning, not a hard failure.
# See https://bob.ibm.com/docs/shell/security/trusted-folders
TRUST_FILE="$HOME/.bob/trustedFolders.json"
if [[ ! -f "$TRUST_FILE" ]] || ! grep -qF "$REPO" "$TRUST_FILE" 2>/dev/null; then
    echo -e "${YELLOW}⚠  This folder doesn't look trusted by Bob yet.${NC}"
    echo -e "   ${DIM}If this run writes no files and never activates the cuga-source-sync skill,${NC}"
    echo -e "   ${DIM}run 'bob' here interactively once and choose \"Trust folder\" first —${NC}"
    echo -e "   ${DIM}otherwise --yolo is silently downgraded to a read-only safe mode.${NC}"
    echo -e "   ${DIM}Also check Bob Settings → Auto-Approve → Skills is enabled.${NC}"
    echo ""
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
    echo "   The skill will update it rather than overwrite."
    echo ""
fi

echo -e "${BOLD}Source sync plan:${NC}"
echo -e "  Source   ${CYAN}migration_from/$SOURCE_NAME${NC}"
echo -e "  Output   ${CYAN}migration_from/$SOURCE_NAME/CLAUDE.md${NC}"
echo ""

# ── Run (foreground) ────────────────────────────────────────────────────────────
echo -e "${BOLD}Running source sync…${NC}"
echo ""
cd "$REPO"

PROMPT="Sync source hints for $SOURCE_NAME — scout migration_from/$SOURCE_NAME and write its CLAUDE.md."

bob --auth-method api-key --yolo -p "$PROMPT"

echo ""
echo -e "${GREEN}✓ Source sync finished — check migration_from/$SOURCE_NAME/CLAUDE.md${NC}"
