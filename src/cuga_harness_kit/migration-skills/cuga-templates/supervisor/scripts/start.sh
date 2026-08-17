#!/usr/bin/env bash
# {{PLACEHOLDER: update the description to match the supervisor name from the spec}}
# Start all MCP servers and the CUGA supervisor backend.
# Run from the project root: bash scripts/start.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PKG_DIR="$ROOT_DIR"  # {{PLACEHOLDER: update if MCP servers live in a subdirectory}}

if [ -f "$ROOT_DIR/.env" ]; then
  set -a; source "$ROOT_DIR/.env"; set +a
  echo "[start] Loaded .env"
fi

# ── Readiness helper ─────────────────────────────────────────────────────────
wait_for_port() {
  local port=$1
  local name=$2
  local max_wait=${3:-30}
  local elapsed=0
  echo "[start] Waiting for $name on port $port..."
  while [ $elapsed -lt $max_wait ]; do
    if lsof -i:"$port" -sTCP:LISTEN > /dev/null 2>&1; then
      echo "[start] $name is ready on port $port"
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  echo "[start] ERROR: $name on port $port did not start within ${max_wait}s" >&2
  return 1
}

# ── Check and kill processes on required ports ───────────────────────────────
# {{PLACEHOLDER: list all ports used by MCP servers and the CUGA backend}}
PORTS_TO_CHECK=(
  # {{PLACEHOLDER: add one port per MCP server, e.g. 8114 8115 8116}}
  8114  # my_data_server
  7860  # CUGA backend
)
echo "[start] Checking for processes on ports ${PORTS_TO_CHECK[*]}..."
for port in "${PORTS_TO_CHECK[@]}"; do
  PID=$(lsof -ti:"$port" 2>/dev/null || true)
  if [ -n "$PID" ]; then
    echo "[start] Port $port in use by PID $PID — killing..."
    kill -9 "$PID" 2>/dev/null || true
    sleep 0.3
  fi
done
echo "[start] All required ports are now available."
echo ""

# ── Start MCP servers ─────────────────────────────────────────────────────────
# {{PLACEHOLDER: add one block per MCP server in the spec}}

echo "[start] Starting my_data_server MCP (port 8114)..."  # {{PLACEHOLDER: update server name and port}}
uv run python "$PKG_DIR/mcp_servers/my_data_server.py" &   # {{PLACEHOLDER: update filename}}
PID_MCP_1=$!

# {{PLACEHOLDER: copy the two lines above for each additional MCP server}}
# echo "[start] Starting my_other_server MCP (port 8115)..."
# uv run python "$PKG_DIR/mcp_servers/my_other_server.py" &
# PID_MCP_2=$!

# ── Wait for MCP servers to be ready ─────────────────────────────────────────
wait_for_port 8114 "my_data_server"   # {{PLACEHOLDER: match each server and port above}}
# wait_for_port 8115 "my_other_server"

# ── Start CUGA backend ────────────────────────────────────────────────────────
# DYNACONF_SUPERVISOR__ENABLED / DYNACONF_SUPERVISOR__CONFIG_PATH are what tell
# cuga.backend.server.main:app to load THIS supervisor_config.yaml instead of
# running in single-agent mode (settings.supervisor.enabled defaults to false).
# This mirrors the exact env vars `cuga start travel_agent` sets before booting
# its own uvicorn process (cuga/cli/main.py, "elif service == 'travel_agent':").
# CONFIG_PATH must be absolute — the backend resolves it relative to os.getcwd().
echo "[start] Starting CUGA backend server on port 7860..."
export DYNACONF_SUPERVISOR__ENABLED=true
export DYNACONF_SUPERVISOR__CONFIG_PATH="$ROOT_DIR/supervisor_config.yaml"
uv run uvicorn cuga.backend.server.main:app --host 0.0.0.0 --port 7860 &
PID_BACKEND=$!
wait_for_port 7860 "CUGA backend"

echo ""
echo "[start] All services started:"
# {{PLACEHOLDER: update the service list to match your spec}}
echo "  my_data_server  : http://localhost:8114"
echo "  CUGA backend    : http://localhost:7860"
echo ""
echo "[start] Press Ctrl+C to stop all services."

# ── Cleanup on exit ───────────────────────────────────────────────────────────
cleanup() {
  echo ""
  echo "[start] Stopping all services..."
  # {{PLACEHOLDER: add $PID_MCP_2 etc. for each additional server}}
  kill "$PID_MCP_1" "$PID_BACKEND" 2>/dev/null || true
  wait 2>/dev/null || true
  echo "[start] Done."
}
trap cleanup INT TERM

wait
