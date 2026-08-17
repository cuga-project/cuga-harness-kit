#!/usr/bin/env bash
# CUGA Migrator — launch script
# Usage:  bash migrate.sh                                          (interactive prompts)
#         bash migrate.sh <source-name> <target>                   (non-interactive)
#         bash migrate.sh <source-name> <target> --stages analyst  (one stage only)
#         bash migrate.sh <source-name> <target> --stages analyst,implementer  (several, in order)
# bash migrate.sh cp4i-res cp4i-cuga
# bash migrate.sh cp4i-res cp4i-cuga --stages analyst
# bash migrate.sh cp4i-res cp4i-cuga --stages analyst,implementer
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
echo -e "${BOLD}${CYAN}║       CUGA Migrator               ║${NC}"
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

# Write env vars to .claude/settings.local.json so the orchestrator and all sub-agents
# (spawned via Agent tool) automatically pick up the same env vars.
mkdir -p "$REPO/.cuga-migrator"
mkdir -p "$REPO/.claude"
SETTINGS_JSON=$(cat <<EOF
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
)
echo "$SETTINGS_JSON" > "$REPO/.claude/settings.local.json"
echo "$SETTINGS_JSON" > "$REPO/.cuga-migrator/run_settings.json"
echo -e "${DIM}Settings written → .claude/settings.local.json, .cuga-migrator/run_settings.json${NC}"

# Print which vars are active
echo -e "${DIM}Environment:${NC}"
[[ -n "$ANTHROPIC_BASE_URL" ]]                        && echo -e "  ${DIM}ANTHROPIC_BASE_URL                   = $ANTHROPIC_BASE_URL${NC}"
[[ -n "$ANTHROPIC_AUTH_TOKEN" ]]                      && echo -e "  ${DIM}ANTHROPIC_AUTH_TOKEN                 = ${ANTHROPIC_AUTH_TOKEN:0:8}…${NC}"
[[ -n "$ANTHROPIC_MODEL" ]]                           && echo -e "  ${DIM}ANTHROPIC_MODEL                      = $ANTHROPIC_MODEL${NC}"
[[ -n "$CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS" ]]   && echo -e "  ${DIM}CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS = $CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS${NC}"
echo ""

# ── Preflight checks ───────────────────────────────────────────────────────────
if ! command -v claude &>/dev/null; then
    echo -e "${RED}✗ claude not found.${NC}"
    echo "  Install Claude Code: https://claude.ai/code"
    exit 1
fi

CLAUDE_VERSION=$(claude --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "0.0.0")
MIN_VERSION="2.1.139"
if [[ "$(printf '%s\n' "$MIN_VERSION" "$CLAUDE_VERSION" | sort -V | head -1)" != "$MIN_VERSION" ]]; then
    echo -e "${YELLOW}⚠  Claude Code $CLAUDE_VERSION detected. Agent View requires $MIN_VERSION+.${NC}"
    echo "   Run: claude update"
    echo "   Continuing anyway — Agent View may not be available."
    echo ""
fi

if [[ ! -d "$REPO/migration_to/cuga-agent" ]]; then
    echo -e "${RED}✗ cuga-agent/ not found at $REPO/migration_to/cuga-agent${NC}"
    echo "  Copy the CUGA SDK repo into migration_to/:"
    echo "    cp -r /path/to/cuga-agent $REPO/migration_to/cuga-agent"
    exit 1
fi

# ── Parse --stages out of the argument list, leaving positionals in place ────────
STAGES=""
POSITIONAL=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --stages) STAGES="${2:-}"; shift 2 ;;
        *) POSITIONAL+=("$1"); shift ;;
    esac
done
# bash 3.2 (macOS default) throws "unbound variable" on "${arr[@]}" for an empty
# array under `set -u` — guard the no-positionals case explicitly.
if [[ ${#POSITIONAL[@]} -gt 0 ]]; then
    set -- "${POSITIONAL[@]}"
else
    set --
fi

if [[ -n "$STAGES" ]]; then
    VALID_STAGES=(analyst implementer test_writer evaluator debugger)
    IFS=',' read -ra STAGE_LIST <<< "$STAGES"
    for i in "${!STAGE_LIST[@]}"; do
        # trim leading/trailing whitespace from each comma-separated part
        r="${STAGE_LIST[$i]}"
        r="${r#"${r%%[![:space:]]*}"}"
        r="${r%"${r##*[![:space:]]}"}"
        STAGE_LIST[$i]="$r"
        if [[ ! " ${VALID_STAGES[*]} " =~ " $r " ]]; then
            echo -e "${RED}✗ Unknown stage: $r${NC}"
            echo "  Valid stages: ${VALID_STAGES[*]}"
            exit 1
        fi
    done
    # normalize back to a clean comma-joined string (trimmed, no stray spaces)
    STAGES=$(IFS=,; echo "${STAGE_LIST[*]}")
fi

# ── Source / target names ──────────────────────────────────────────────────────
SOURCE_NAME="${1:-}"
TARGET_NAME="${2:-}"

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

if [[ -z "$TARGET_NAME" ]]; then
    read -rp "  Target name (output folder under migration_to/): " TARGET_NAME
fi

echo ""

# ── Validate source ────────────────────────────────────────────────────────────
SOURCE_PATH="$REPO/migration_from/$SOURCE_NAME"
if [[ ! -d "$SOURCE_PATH" ]]; then
    echo -e "${RED}✗ Source not found: migration_from/$SOURCE_NAME${NC}"
    exit 1
fi

# ── Ground truth hint ──────────────────────────────────────────────────────────
GT_PATH="$REPO/migration_to/data/ground_truth"
mkdir -p "$GT_PATH"
mkdir -p "$REPO/.cuga-migrator"

GT_COUNT=$(find "$GT_PATH" -name "*.txt" 2>/dev/null | wc -l | tr -d ' ')
if [[ "$GT_COUNT" -eq 0 ]]; then
    echo -e "${YELLOW}ℹ  No ground truth files found at:${NC}"
    echo -e "   ${DIM}migration_to/data/ground_truth/${NC}"
    echo "   The test_writer agent will ask you to provide them during the run."
    echo "   Place .txt trace flow files there before the test stage, or skip tests."
    echo ""
fi

# ── User request ──────────────────────────────────────────────────────────────
# .cuga-migrator/user_request.md is a standing file, not a per-run prompt — edit it yourself
# before running migrate.sh if you have a special request; the orchestrator reads it at the start
# of every run regardless of whether it's empty. Create it with just the header if it's missing,
# so it's discoverable without clobbering anything you've already written there.
USER_REQUEST_FILE="$REPO/.cuga-migrator/user_request.md"
if [[ ! -f "$USER_REQUEST_FILE" ]]; then
    printf '# User Request\n' > "$USER_REQUEST_FILE"
fi

# ── Summary ────────────────────────────────────────────────────────────────────
echo -e "${BOLD}Migration plan:${NC}"
echo -e "  Source   ${CYAN}migration_from/$SOURCE_NAME${NC}"
echo -e "  Target   ${CYAN}migration_to/$TARGET_NAME${NC}"
echo -e "  SDK      ${DIM}cuga-agent/${NC}"
echo -e "  State    ${DIM}.cuga-migrator/${NC}"
echo -e "  Request  ${DIM}.cuga-migrator/user_request.md (edit it before running to set one)${NC}"
[[ -n "$STAGES" ]] && echo -e "  Stage(s) ${YELLOW}$STAGES only, in order (stage-only mode)${NC}"
echo ""

# ── Dispatch background session ────────────────────────────────────────────────
echo -e "${BOLD}Dispatching migration session…${NC}"
cd "$REPO"

if [[ -n "$STAGES" ]]; then
    SESSION_NAME="migrate → $TARGET_NAME [$STAGES]"
    claude --bg "/migrate $SOURCE_NAME $TARGET_NAME --stages $STAGES" --name "$SESSION_NAME" 2>/dev/null || {
        PROMPT="You are the CUGA Migration Orchestrator. Run /migrate with source=$SOURCE_NAME target=$TARGET_NAME stages=$STAGES (stage-only mode — run ONLY the listed stage(s), in order, per .claude/commands/migrate.md's 'Stage-only mode (--stages)' section). The repo root is $REPO. Follow the instructions in .claude/commands/migrate.md."
        claude --bg "$PROMPT" --name "$SESSION_NAME"
    }
else
    SESSION_NAME="migrate → $TARGET_NAME"
    claude --bg "/migrate $SOURCE_NAME $TARGET_NAME" --name "$SESSION_NAME" 2>/dev/null || {
        # Fallback: some versions don't support slash commands in --bg
        PROMPT="You are the CUGA Migration Orchestrator. Run /migrate with source=$SOURCE_NAME target=$TARGET_NAME. The repo root is $REPO. Follow the instructions in .claude/commands/migrate.md."
        claude --bg "$PROMPT" --name "$SESSION_NAME"
    }
fi

# Kill the background session on any exit (normal, Ctrl+C, error, TERM)
_CLEANUP_DONE=0
cleanup() {
    [[ "$_CLEANUP_DONE" -eq 1 ]] && return
    _CLEANUP_DONE=1
    echo ""
    echo -e "${YELLOW}Stopping migration session…${NC}"
    claude daemon stop --any 2>/dev/null || true
    echo -e "${DIM}Session stopped.${NC}"
}
# EXIT fires on all exit paths (normal, Ctrl+C, TERM, set -e errors).
# INT/TERM call exit explicitly to guarantee EXIT fires even if claude agents
# swallows SIGINT and returns 0 (which would bypass an INT-only trap).
trap cleanup EXIT
trap 'exit 130' INT TERM

echo ""
echo -e "${GREEN}✓ Session dispatched: ${BOLD}$SESSION_NAME${NC}"
echo ""
echo -e "${DIM}Controls in Agent View:${NC}"
echo -e "  ${CYAN}Space${NC}   peek at current output and reply to human-gate questions"
echo -e "  ${CYAN}Enter${NC}   attach to the session (full conversation)"
echo -e "  ${CYAN}←${NC}       detach back to Agent View"
echo -e "  ${CYAN}?${NC}       show all shortcuts"
echo ""

# ── Open Agent View ────────────────────────────────────────────────────────────
echo -e "${BOLD}Opening Agent View…${NC}"
echo ""
claude agents --cwd "$REPO"
