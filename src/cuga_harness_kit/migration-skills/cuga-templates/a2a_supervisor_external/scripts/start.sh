#!/usr/bin/env bash
# {{PLACEHOLDER: update the description to match the supervisor name from the spec}}
# Start all external A2A agents and the CUGA supervisor backend.
# Run from the project root: bash scripts/start.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$ROOT_DIR/.env" ]; then
    set -a; source "$ROOT_DIR/.env"; set +a
    echo "[start] Loaded .env"
fi

# ── Readiness helper ──────────────────────────────────────────────────────────
wait_for_port() {
    local port=$1 name=$2 max_wait=${3:-30} elapsed=0
    echo "[start] Waiting for $name on port $port..."
    while [ $elapsed -lt $max_wait ]; do
        if lsof -i:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
            echo "[start] $name ready on port $port"
            return 0
        fi
        sleep 1; elapsed=$((elapsed + 1))
    done
    echo "[start] ERROR: $name did not start within ${max_wait}s" >&2
    return 1
}

# ── Kill any processes on required ports ─────────────────────────────────────
# {{PLACEHOLDER: list all A2A agent ports and 7860 for the CUGA backend}}
for port in 8001 8002 7860; do   # {{PLACEHOLDER: update to match your agent ports}}
    PID=$(lsof -ti:"$port" 2>/dev/null || true)
    [ -n "$PID" ] && { echo "[start] Port $port in use by PID $PID — killing"; kill -9 "$PID" 2>/dev/null || true; sleep 0.3; }
done
echo "[start] All required ports are now available."
echo ""

# ── Start external A2A agents ─────────────────────────────────────────────────
# {{PLACEHOLDER: add one block per A2A agent in the spec}}

echo "[start] Starting agent_one A2A server (port 8001)..."  # {{PLACEHOLDER: update agent name and port}}
uv run python "$ROOT_DIR/a2a_agents/agent_one.py" &           # {{PLACEHOLDER: update filename}}
PID_AGENT_ONE=$!

echo "[start] Starting agent_two A2A server (port 8002)..."  # {{PLACEHOLDER: update agent name and port, or remove}}
uv run python "$ROOT_DIR/a2a_agents/agent_two.py" &           # {{PLACEHOLDER: update filename}}
PID_AGENT_TWO=$!

# {{PLACEHOLDER: copy the two lines above for each additional A2A agent}}

# ── Wait for agents to be ready ───────────────────────────────────────────────
wait_for_port 8001 "agent_one"  # {{PLACEHOLDER: match each agent and port above}}
wait_for_port 8002 "agent_two"  # {{PLACEHOLDER: match each agent and port above}}

# ── Start CUGA backend ─────────────────────────────────────────────────────────
# DYNACONF_SUPERVISOR__ENABLED / DYNACONF_SUPERVISOR__CONFIG_PATH are what tell
# cuga.backend.server.main:app to load THIS supervisor_config.yaml (via
# cuga_graph/graph.py's `load_supervisor_config`) instead of running in
# single-agent mode (settings.supervisor.enabled defaults to false). This
# mirrors the exact env vars `cuga start travel_agent` sets before booting its
# own uvicorn process (cuga/cli/main.py, "elif service == 'travel_agent':").
# CONFIG_PATH must be absolute — the backend resolves it relative to os.getcwd().
echo "[start] Starting CUGA backend (port 7860)..."
cd "$ROOT_DIR"
CUGA_FOLDER="$ROOT_DIR/.cuga" \
    DYNACONF_SUPERVISOR__ENABLED=true \
    DYNACONF_SUPERVISOR__CONFIG_PATH="$ROOT_DIR/supervisor_config.yaml" \
    uv run uvicorn cuga.backend.server.main:app --host 0.0.0.0 --port 7860 &
PID_BACKEND=$!
wait_for_port 7860 "CUGA backend"

echo ""
echo "[start] All services running:"
# {{PLACEHOLDER: update the service list to match your agents}}
echo "  agent_one    : http://localhost:8001"
echo "  agent_two    : http://localhost:8002"
echo "  CUGA backend : http://localhost:7860"
echo ""
echo "[start] Press Ctrl+C to stop all services."

# ── Cleanup on exit ────────────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "[start] Stopping all services..."
    # {{PLACEHOLDER: add $PID_AGENT_THREE etc. for each additional agent}}
    kill "$PID_AGENT_ONE" "$PID_AGENT_TWO" "$PID_BACKEND" 2>/dev/null || true
    wait 2>/dev/null || true
    echo "[start] Done."
}
trap cleanup INT TERM

wait
