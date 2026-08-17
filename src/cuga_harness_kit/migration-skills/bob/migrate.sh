#!/usr/bin/env bash
# CUGA Migrator (Bob) — launch script
# Usage:  bash migrate.sh                                          (interactive prompts)
#         bash migrate.sh <source-name> <target>                   (full pipeline)
#         bash migrate.sh <source-name> <target> --stages analyst  (one stage only)
#         bash migrate.sh <source-name> <target> --stages analyst,implementer  (several, in order)
#
# Ports cuga-migrator/migrate.sh to Bob Shell. Always dispatches interactively —
# `bob -p "<prompt>"` (Bob Shell's non-interactive CLI mode) is documented as
# single-shot and non-resumable, so it can't reliably handle the trust-folder
# prompt, the skill-activation prompt, or (full pipeline) the two human review
# gates. This script does the usual prep (credentials, preflight checks, plan
# summary), prints the constructed request, then opens a plain interactive `bob`
# session for you to paste that request into as your first message. `--stages`
# only changes what the supervisor is told to do — run just these stage(s), in
# this order, instead of the full pipeline — not how the session is dispatched;
# everything else about the interaction is identical either way.
#
# Two more things this script does NOT attempt, because they aren't documented
# for Bob:
#   - background dispatch + Agent View (Claude Code's `claude --bg ... --name`
#     + `claude agents`) — there's no equivalent, so this just runs `bob` in the
#     foreground; you're present for the whole run, not able to detach/reattach.
#   - an explicit "run skill X" flag — there isn't one. Prompts are phrased to
#     match the cuga-migrator skill's `description` field; Bob's own
#     description-matching decides whether to activate it.
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
echo -e "${BOLD}${CYAN}║     CUGA Migrator (Bob)           ║${NC}"
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
    echo -e "   ${DIM}Expect a \"Trust folder?\" prompt right after bob opens below — choose${NC}"
    echo -e "   ${DIM}\"Trust folder\" (or \"Trust parent folder\") to continue.${NC}"
    echo -e "   ${DIM}Also check Bob Settings → Auto-Approve → Skills is enabled, so you${NC}"
    echo -e "   ${DIM}aren't separately asked to approve cuga-migrator's activation.${NC}"
    echo ""
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
    echo "   The test_writer stage will ask you to provide them during the run."
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

# ── Run ──────────────────────────────────────────────────────────────────────
# Always interactive, full pipeline or --stages alike. `bob -p` is documented as
# single-shot and non-resumable — it can't pause mid-run and wait for a reply, so
# it can't reliably handle the trust-folder prompt, the skill-activation prompt,
# or (full pipeline only) the two review gates. --stages only changes what the
# supervisor is told to do (run just these stage(s), in this order, instead of
# the full pipeline) — not how the session is dispatched. There is no documented
# flag to seed an interactive session with an initial message, so this opens a
# plain interactive `bob` session and asks you to paste the request yourself as
# your first message; from there Bob's normal prompts (trust, skill activation,
# file writes, review gates if any) all work as usual.
cd "$REPO"

if [[ -n "$STAGES" ]]; then
    PROMPT="Run ONLY these stage(s) of the migration pipeline, in this order: $STAGES (per .bob/skills/cuga-migrator/SKILL.md's 'Stage-only mode (--stages)' section) for migration_from/$SOURCE_NAME -> migration_to/$TARGET_NAME. Do not run any stage not in that list."
else
    PROMPT="Migrate the source agent system in migration_from/$SOURCE_NAME to a CUGA SDK implementation in migration_to/$TARGET_NAME."
fi

echo -e "${BOLD}Opening an interactive bob session.${NC}"
echo -e "${DIM}Paste this as your first message once it starts:${NC}"
echo ""
echo -e "${CYAN}$PROMPT${NC}"
echo ""

# bob's interactive TUI typically clears/takes over the terminal on launch, which
# wipes the prompt printed above before you'd ever get to read it back — leaving
# you looking at an idle bob prompt with nothing obvious to type. Put the prompt
# somewhere that survives that: the clipboard (so it's a plain paste), and a file
# (so it's still readable even without clipboard access, e.g. over SSH).
PROMPT_FILE="$REPO/.cuga-migrator/last_prompt.txt"
mkdir -p "$(dirname "$PROMPT_FILE")"
printf '%s\n' "$PROMPT" > "$PROMPT_FILE"

if command -v pbcopy &>/dev/null; then
    printf '%s' "$PROMPT" | pbcopy
    echo -e "${GREEN}✓ Copied to your clipboard — just paste (Cmd+V) as your first message in bob.${NC}"
elif command -v xclip &>/dev/null; then
    printf '%s' "$PROMPT" | xclip -selection clipboard
    echo -e "${GREEN}✓ Copied to your clipboard — just paste as your first message in bob.${NC}"
elif command -v xsel &>/dev/null; then
    printf '%s' "$PROMPT" | xsel --clipboard --input
    echo -e "${GREEN}✓ Copied to your clipboard — just paste as your first message in bob.${NC}"
else
    echo -e "${YELLOW}ℹ  No clipboard tool found (pbcopy/xclip/xsel) — copy the text above manually.${NC}"
fi
echo -e "${DIM}Also saved to $PROMPT_FILE if you need it again.${NC}"
echo ""
read -rp "Press Enter to open bob… " _
echo ""

bob --auth-method api-key

echo ""
echo -e "${GREEN}✓ Session ended.${NC}"
