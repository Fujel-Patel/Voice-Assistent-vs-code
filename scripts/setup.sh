#!/usr/bin/env bash
# =============================================================
# Jarvis Voice Assistant — One-Command Setup Script
# =============================================================
# Usage: bash scripts/setup.sh
#
# This script:
#   1. Creates the Python virtual environment
#   2. Installs all Python dependencies
#   3. Installs all Node.js dependencies
#   4. Creates .env from .env.example (if not present)
#   5. Creates the data/ directory for SQLite
# =============================================================

set -euo pipefail

# Terminal colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo -e "${CYAN}${BOLD}"
echo "  ╔═══════════════════════════════════╗"
echo "  ║   Jarvis Voice Assistant Setup    ║"
echo "  ╚═══════════════════════════════════╝"
echo -e "${NC}"

# ── Check dependencies ──────────────────────────────────
check_dep() {
  if ! command -v "$1" &>/dev/null; then
    echo -e "${RED}✗ Missing dependency: $1${NC}"
    echo -e "  Install it and re-run this script."
    exit 1
  fi
  echo -e "${GREEN}✓ Found: $1 $(command -v "$1")${NC}"
}

echo -e "\n${BOLD}Checking system dependencies...${NC}"
check_dep python3
check_dep pip3
check_dep node
check_dep npm

# Verify Python version (3.10+)
PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(echo "$PYTHON_VER" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VER" | cut -d. -f2)
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
  echo -e "${RED}✗ Python 3.10+ required, found $PYTHON_VER${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VER (compatible)${NC}"

# ── Python virtual environment ──────────────────────────
echo -e "\n${BOLD}Setting up Python virtual environment...${NC}"
cd "$BACKEND_DIR"

if [ ! -d ".venv" ]; then
  echo -e "${CYAN}Creating .venv ...${NC}"
  python3 -m venv .venv
  echo -e "${GREEN}✓ Virtual environment created${NC}"
else
  echo -e "${YELLOW}→ .venv already exists, skipping creation${NC}"
fi

# Activate venv
source .venv/bin/activate

echo -e "${CYAN}Upgrading pip...${NC}"
pip install --upgrade pip -q

echo -e "${CYAN}Installing Python dependencies (this may take a few minutes)...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Explicitly install dependencies that often cause issues with openwakeword
echo -e "${CYAN}Installing AI runtime dependencies...${NC}"
# Try tflite-runtime, then its newer name ai-edge-litert, then just stick with onnxruntime
if ! pip install tflite-runtime -q 2>/dev/null; then
  echo -e "${YELLOW}⚠ tflite-runtime not found. Trying ai-edge-litert (modern replacement)...${NC}"
  pip install ai-edge-litert -q 2>/dev/null || echo -e "${YELLOW}⚠ TFLite runtimes unavailable. openWakeWord will use ONNX only.${NC}"
fi
pip install onnxruntime-gpu onnxruntime -q 2>/dev/null || pip install onnxruntime -q

echo -e "${CYAN}Installing openWakeWord...${NC}"
if ! pip install openwakeword==0.6.0 -q; then
  echo -e "${YELLOW}⚠ Regular openWakeWord install failed (likely dependency conflict). Trying ONNX-only mode...${NC}"
  pip install --no-deps openwakeword==0.6.0 -q
  echo -e "${GREEN}✓ openWakeWord installed (ONNX-only mode)${NC}"
else
  echo -e "${GREEN}✓ openWakeWord installed${NC}"
fi

if command -v apt &>/dev/null; then
  echo -e "${CYAN}Installing Linux system packages...${NC}"
  # Silence architecture warnings and skip recommendations
  sudo apt-get update -qq -o Acquire::Languages=none
  sudo apt-get install -y -qq --no-install-recommends tesseract-ocr portaudio19-dev
fi

deactivate

# ── Node.js dependencies ─────────────────────────────────
echo -e "\n${BOLD}Installing Node.js dependencies...${NC}"
cd "$FRONTEND_DIR"
# Use --no-audit to skip the high-volume vulnerability warnings during setup
npm install --no-audit --quiet
echo -e "${GREEN}✓ Node.js dependencies installed${NC}"

# ── Environment file ─────────────────────────────────────
echo -e "\n${BOLD}Setting up environment variables...${NC}"
cd "$PROJECT_ROOT"

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo -e "${YELLOW}⚠ .env created from .env.example${NC}"
  echo -e "  ${YELLOW}→ Open .env and add your API keys before running Jarvis${NC}"
else
  echo -e "${YELLOW}→ .env already exists, skipping${NC}"
fi

# ── Data directory ──────────────────────────────────────
mkdir -p "$BACKEND_DIR/data"
mkdir -p "$BACKEND_DIR/logs"
mkdir -p "$HOME/.jarvis/models/tts"
echo -e "${GREEN}✓ Data and model directories created at $HOME/.jarvis/models/tts${NC}"

echo -e "${CYAN}Downloading required models...${NC}"
"$BACKEND_DIR/.venv/bin/python" "$SCRIPT_DIR/download_models.py" || {
  echo -e "${YELLOW}⚠ Model download failed. You can rerun scripts/download_models.py later.${NC}"
}

# ── Done ─────────────────────────────────────────────────
echo -e "\n${GREEN}${BOLD}"
echo "  ╔═══════════════════════════════════╗"
echo "  ║     Setup Complete! ✅             ║"
echo "  ╚═══════════════════════════════════╝"
echo -e "${NC}"
echo -e "Next steps:"
echo -e "  1. Add your API keys to ${CYAN}.env${NC}"
echo -e "  2. Prepare Moonshine/Piper models: ${CYAN}backend/.venv/bin/python scripts/download_models.py${NC}"
echo -e "  3. Start dev environment:  ${CYAN}bash scripts/dev.sh${NC}"
echo ""
