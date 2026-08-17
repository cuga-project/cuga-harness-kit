#!/usr/bin/env bash
# Run this after updating migration_to/cuga-agent/ to a new SDK version.
# Reads the SDK source and updates templates so future migrations produce
# accurate specs.
#
# Usage: ./cuga_sync.sh
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
echo -e "${BOLD}${CYAN}║   CUGA Template Sync (Bob)        ║${NC}"
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

if [[ ! -d "$REPO/migration_to/cuga-agent" ]]; then
    echo -e "${RED}✗ cuga-agent/ not found at $REPO/migration_to/cuga-agent${NC}"
    echo "  Copy the CUGA SDK repo into migration_to/:"
    echo "    cp -r /path/to/cuga-agent $REPO/migration_to/cuga-agent"
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
    echo -e "   ${DIM}If this run writes no files and never activates the cuga-template-sync skill,${NC}"
    echo -e "   ${DIM}run 'bob' here interactively once and choose \"Trust folder\" first —${NC}"
    echo -e "   ${DIM}otherwise --yolo is silently downgraded to a read-only safe mode.${NC}"
    echo -e "   ${DIM}Also check Bob Settings → Auto-Approve → Skills is enabled.${NC}"
    echo ""
fi

mkdir -p "$REPO/.cuga-migrator"

# ── Run (foreground) ────────────────────────────────────────────────────────────
echo -e "${BOLD}Running template sync…${NC}"
echo ""
cd "$REPO"

PROMPT="Sync CUGA templates against the SDK — check cuga-templates/ for drift against migration_to/cuga-agent/ and fix it."

bob --auth-method api-key --yolo -p "$PROMPT"

echo ""
echo -e "${GREEN}✓ Template sync finished — check .cuga-migrator/sync_report.md${NC}"
