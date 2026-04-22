#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
VENV_DIR="$BACKEND_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"
LOG_DIR="$BACKEND_DIR/logs/dev"
REQ_HASH_FILE="$VENV_DIR/.requirements.sha256"
VENV_ACTIVATED_BY_SCRIPT=0

# Log colors for highlighting
LOG_RED='\033[0;31m'
LOG_YELLOW='\033[1;33m'
LOG_GREEN='\033[0;32m'
LOG_NC='\033[0m'

# Log filter to highlight errors and warnings and remove common noise
filter_logs() {
  local prefix="$1"
  sed -u "s/^/[${prefix}] /" | sed -u "
    s/\(ERROR\|Exception\|Critical\|Fail\)/${LOG_RED}&${LOG_NC}/gI;
    s/\(WARN\|Warning\)/${LOG_YELLOW}&${LOG_NC}/gI;
    s/\(SUCCESS\|OK\|Ready\)/${LOG_GREEN}&${LOG_NC}/gI;
    /HMR update/d;
    /GET \/health/d;
  "
}

echo -e "${CYAN}${BOLD}"
echo "  ╔═══════════════════════════════════╗"
echo "  ║    Jarvis Dev Environment         ║"
echo "  ╚═══════════════════════════════════╝"
echo -e "${NC}"

echo -e "${CYAN}[JARVIS] Starting development environment...${NC}"

VENV_CREATED=false

requirements_checksum() {
  sha256sum "$BACKEND_DIR/requirements.txt" | awk '{print $1}'
}

ensure_openwakeword_installed() {
  if [ "${JARVIS_SKIP_OPENWAKEWORD_INSTALL:-0}" = "1" ]; then
    echo -e "${YELLOW}[JARVIS] Skipping openWakeWord install (JARVIS_SKIP_OPENWAKEWORD_INSTALL=1).${NC}"
    return
  fi

  if "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import openwakeword
PY
  then
    return
  fi

  echo -e "${CYAN}[JARVIS] Installing openWakeWord (ONNX-only fallback)...${NC}"
  if ! "$PYTHON_BIN" -m pip install --disable-pip-version-check --no-deps openwakeword==0.6.0; then
    echo -e "${YELLOW}[WARN] openWakeWord install failed. Wake-word detection may be unavailable.${NC}"
  fi
}

if ! command -v python3 >/dev/null 2>&1; then
  echo -e "${RED}[ERROR] python3 not found. Install Python 3.11+ first.${NC}"
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo -e "${CYAN}[JARVIS] Creating Python venv at backend/.venv...${NC}"
  python3 -m venv "$VENV_DIR"
  VENV_CREATED=true
fi

recreate_venv() {
  echo -e "${YELLOW}[JARVIS] Recreating broken backend/.venv...${NC}"
  rm -rf "$VENV_DIR"
  python3 -m venv "$VENV_DIR"
  VENV_CREATED=true
}

repair_pip() {
  echo -e "${YELLOW}[JARVIS] Repairing pip in backend/.venv...${NC}"
  "$PYTHON_BIN" -m ensurepip --upgrade >/dev/null 2>&1 || true
  "$PYTHON_BIN" -m pip install --upgrade pip >/dev/null 2>&1 || true
}

if [ ! -x "$PYTHON_BIN" ]; then
  recreate_venv
fi

if ! "$PYTHON_BIN" -V >/dev/null 2>&1; then
  recreate_venv
fi

if [ ! -x "$PIP_BIN" ] || ! "$PIP_BIN" --version >/dev/null 2>&1; then
  repair_pip
fi

if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
  recreate_venv
  repair_pip
fi

if [[ "${VIRTUAL_ENV:-}" != "$VENV_DIR" ]]; then
  # Keep tool behavior consistent even when user forgot to activate backend/.venv.
  source "$VENV_DIR/bin/activate"
  VENV_ACTIVATED_BY_SCRIPT=1
fi

REQ_HASH="$(requirements_checksum)"
INSTALLED_REQ_HASH=""
if [ -f "$REQ_HASH_FILE" ]; then
  INSTALLED_REQ_HASH="$(cat "$REQ_HASH_FILE" 2>/dev/null || true)"
fi

if [ "${JARVIS_SKIP_PIP_INSTALL:-0}" = "1" ]; then
  echo -e "${YELLOW}[JARVIS] Skipping dependency install (JARVIS_SKIP_PIP_INSTALL=1).${NC}"
  ensure_openwakeword_installed
elif [ "${JARVIS_FORCE_PIP_INSTALL:-0}" = "1" ] || [ "$VENV_CREATED" = true ] || [ "$REQ_HASH" != "$INSTALLED_REQ_HASH" ]; then
  echo -e "${CYAN}[JARVIS] Installing backend dependencies...${NC}"
  if "$PYTHON_BIN" -m pip install --disable-pip-version-check -r "$BACKEND_DIR/requirements.txt"; then
    echo "$REQ_HASH" > "$REQ_HASH_FILE"
    ensure_openwakeword_installed
  else
    if [ "$VENV_CREATED" = true ]; then
      echo -e "${RED}[ERROR] Dependency installation failed in a fresh virtual environment.${NC}"
      exit 1
    fi
    echo -e "${YELLOW}[WARN] Dependency installation failed. Continuing with existing environment.${NC}"
  fi
else
  echo -e "${GREEN}[JARVIS] Backend dependencies unchanged; skipping pip install.${NC}"
  ensure_openwakeword_installed
fi

if [ ! -f "$PROJECT_ROOT/.env" ]; then
  echo -e "${RED}[ERROR] .env file missing. Copy .env.example and fill in API keys.${NC}"
  exit 1
fi

set -a
source "$PROJECT_ROOT/.env"
set +a

have_any_brain_provider=false
for key in "${ANTHROPIC_API_KEY:-}" "${GEMINI_API_KEY:-}" "${GROQ_API_KEY:-}" "${OPENROUTER_API_KEY:-}"; do
  if [ -n "$key" ]; then
    have_any_brain_provider=true
    break
  fi
done

if [ "$have_any_brain_provider" = false ] && [ -z "${OLLAMA_BASE_URL:-}" ]; then
  echo -e "${RED}[ERROR] No AI provider configured. Set at least one provider key (Anthropic/Gemini/Groq/OpenRouter) or OLLAMA_BASE_URL.${NC}"
  exit 1
fi

if [ -z "${ELEVENLABS_API_KEY:-}" ]; then
  echo -e "${YELLOW}[WARN] ELEVENLABS_API_KEY is missing. Local TTS fallback will be used.${NC}"
fi

is_port_in_use() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp 2>/dev/null | awk -v p=":${port}" '$4 ~ p {found=1} END {exit !found}'
    return
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
    return
  fi
  return 1
}

is_health_endpoint_ready() {
  if command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time 2 "http://127.0.0.1:8765/health" >/dev/null 2>&1
    return
  fi

  "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import json
import urllib.request

with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=2) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    if not data.get("ok"):
        raise SystemExit(1)
PY
}

kill_port_processes() {
  local port="$1"
  local pids="$(port_pids "$port")"

  if [ -n "${pids// }" ]; then
    echo -e "${YELLOW}[JARVIS] Port ${port} is busy. Stopping processes: ${pids}${NC}"
    for pid in $pids; do
      kill "$pid" 2>/dev/null || true
    done

    for _ in $(seq 1 10); do
      if ! is_port_in_use "$port"; then
        break
      fi
      sleep 0.3
    done

    if is_port_in_use "$port"; then
      pids="$(port_pids "$port")"
      if [ -n "${pids// }" ]; then
        echo -e "${YELLOW}[JARVIS] Port ${port} still busy. Force killing: ${pids}${NC}"
        for pid in $pids; do
          kill -9 "$pid" 2>/dev/null || true
        done
        sleep 0.3
      fi
    fi
  fi
}

port_pids() {
  local port="$1"

  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | tr '\n' ' '
    return
  fi

  if command -v ss >/dev/null 2>&1; then
    ss -ltnp 2>/dev/null | awk -v p=":${port}" '$4 ~ p {print $NF}' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | tr '\n' ' '
    return
  fi
}

kill_port_processes 8765
kill_port_processes 5173

if is_port_in_use 8765; then
  echo -e "${RED}[ERROR] Port 8765 is still in use after cleanup.${NC}"
  exit 1
fi

if is_port_in_use 5173; then
  echo -e "${RED}[ERROR] Port 5173 is still in use after cleanup.${NC}"
  exit 1
fi

mkdir -p "$LOG_DIR"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKEND_LOG="$LOG_DIR/backend_${TIMESTAMP}.log"
FRONTEND_LOG="$LOG_DIR/frontend_${TIMESTAMP}.log"

echo -e "${CYAN}[JARVIS] Logs:${NC}"
echo -e "  Backend  -> $BACKEND_LOG"
echo -e "  Frontend -> $FRONTEND_LOG"

cleanup() {
  trap - EXIT INT TERM

  if [[ "${CLEANED_UP:-0}" == "1" ]]; then
    return
  fi
  CLEANED_UP=1

  echo -e "\n${YELLOW}[JARVIS] Stopping services...${NC}"

  stop_pid() {
    local pid="$1"
    [ -z "$pid" ] && return

    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      pkill -TERM -P "$pid" 2>/dev/null || true
      for _ in $(seq 1 10); do
        if ! kill -0 "$pid" 2>/dev/null; then
          break
        fi
        sleep 0.2
      done
      if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
        pkill -KILL -P "$pid" 2>/dev/null || true
      fi
      wait "$pid" 2>/dev/null || true
    fi
  }

  if [ -n "${BACKEND_PID:-}" ]; then
    stop_pid "$BACKEND_PID"
  fi

  if [ -n "${FRONTEND_PID:-}" ]; then
    stop_pid "$FRONTEND_PID"
  fi

  pkill -TERM -P $$ 2>/dev/null || true
  kill_port_processes 8765
  kill_port_processes 5173

  if [[ "$VENV_ACTIVATED_BY_SCRIPT" == "1" ]] && type deactivate >/dev/null 2>&1; then
    deactivate || true
  fi

  echo -e "${RED}[JARVIS] Stopped.${NC}"
}
trap cleanup EXIT INT TERM

echo -e "${GREEN}[JARVIS] Starting backend on :8765...${NC}"
cd "$PROJECT_ROOT"
stdbuf -oL -eL "$PYTHON_BIN" backend/main.py \
  > >(filter_logs "Backend" | tee -a "$BACKEND_LOG") \
  2>&1 &
BACKEND_PID=$!

echo -e "${CYAN}[JARVIS] Waiting for backend readiness (ws required, /health probe optional)...${NC}"
backend_ready=false
health_ready=false
BACKEND_READY_TIMEOUT_SECONDS="${JARVIS_BACKEND_READY_TIMEOUT_SECONDS:-120}"
BACKEND_READY_POLL_INTERVAL="${JARVIS_BACKEND_READY_POLL_INTERVAL_SECONDS:-0.5}"
BACKEND_READY_MAX_POLLS="$("$PYTHON_BIN" - <<PY
timeout_seconds = float(${BACKEND_READY_TIMEOUT_SECONDS})
poll_interval = float(${BACKEND_READY_POLL_INTERVAL})
if poll_interval <= 0:
  poll_interval = 0.5
print(max(1, int(timeout_seconds / poll_interval)))
PY
)"

is_pid_running() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null
}

for _ in $(seq 1 "$BACKEND_READY_MAX_POLLS"); do
  if ! is_pid_running "$BACKEND_PID"; then
    echo -e "${RED}[ERROR] Backend process exited before becoming ready.${NC}"
    tail -n 60 "$BACKEND_LOG" || true
    exit 1
  fi

  if is_port_in_use 8765; then
    backend_ready=true
    if is_health_endpoint_ready; then
      health_ready=true
    fi

    if [ "${JARVIS_REQUIRE_HEALTH_PORT:-0}" = "1" ] && [ "$health_ready" = false ]; then
      sleep "$BACKEND_READY_POLL_INTERVAL"
      continue
    fi

    break
  fi
  sleep "$BACKEND_READY_POLL_INTERVAL"
done

if [ "$backend_ready" = false ]; then
  echo -e "${RED}[ERROR] Backend did not start on port 8765 in time.${NC}"
  tail -n 60 "$BACKEND_LOG" || true
  exit 1
fi

if [ "$health_ready" = true ]; then
  echo -e "${GREEN}[JARVIS] Backend ready (ws+/health).${NC}"
elif [ "${JARVIS_REQUIRE_HEALTH_PORT:-0}" = "1" ]; then
  echo -e "${RED}[ERROR] FastAPI health endpoint did not become ready (JARVIS_REQUIRE_HEALTH_PORT=1).${NC}"
  tail -n 60 "$BACKEND_LOG" || true
  exit 1
else
  echo -e "${YELLOW}[JARVIS] Backend ready (ws only). /health probe not yet ready.${NC}"
fi

echo -e "${GREEN}[JARVIS] Starting frontend on :5173...${NC}"
cd "$FRONTEND_DIR"
stdbuf -oL -eL npm run dev \
  > >(filter_logs "Frontend" | tee -a "$FRONTEND_LOG") \
  2>&1 &
FRONTEND_PID=$!

echo -e "${GREEN}[JARVIS] Both services running. Open http://localhost:5173${NC}"
wait "$BACKEND_PID" "$FRONTEND_PID"
