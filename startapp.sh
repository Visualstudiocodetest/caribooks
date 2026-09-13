#!/usr/bin/env bash
set -euo pipefail

# Starts backend (FastAPI/uvicorn) + frontend (Next.js) together.
# Usage:
#   bash startapp.sh
# Optional env vars:
#   BACKEND_BASE_URL=http://127.0.0.1:8000
#   BACKEND_HOST=127.0.0.1
#   BACKEND_PORT=8000
#   FRONTEND_PORT=3000

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://${BACKEND_HOST}:${BACKEND_PORT}}"

command -v npm >/dev/null 2>&1 || { echo "npm not found"; exit 1; }

# Use the backend's own venv rather than whatever `python3` resolves to on
# PATH -- a system/global interpreter won't have the project's dependencies
# installed, and can even be a different architecture (e.g. an x86_64 build
# on Apple Silicon), which fails obscurely deep inside a C-extension import.
PYTHON_BIN="${ROOT_DIR}/backend/venv/bin/python3"
[[ -x "$PYTHON_BIN" ]] || { echo "backend/venv not found -- run: python3 -m venv backend/venv && backend/venv/bin/pip install -r backend/requirements.txt"; exit 1; }

backend_pid=""
frontend_pid=""

cleanup() {
	echo
	echo "Stopping servers..."
	if [[ -n "${frontend_pid}" ]]; then kill "${frontend_pid}" 2>/dev/null || true; fi
	if [[ -n "${backend_pid}" ]]; then kill "${backend_pid}" 2>/dev/null || true; fi
	wait 2>/dev/null || true
}

trap cleanup INT TERM EXIT

echo "Starting backend on ${BACKEND_BASE_URL}..."
cd "${ROOT_DIR}/backend"
FRONTEND_ORIGINS="http://127.0.0.1:${FRONTEND_PORT},http://localhost:${FRONTEND_PORT}" \
	"${PYTHON_BIN}" -m uvicorn main:app --reload --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" &
backend_pid=$!

echo "Starting frontend on http://127.0.0.1:${FRONTEND_PORT} (calling FastAPI directly)..."
cd "${ROOT_DIR}/frontend"
BACKEND_BASE_URL="${BACKEND_BASE_URL}" NEXT_PUBLIC_BACKEND_BASE_URL="${BACKEND_BASE_URL}" npm run dev -- --port "${FRONTEND_PORT}" &
frontend_pid=$!

echo
echo "Backend:   ${BACKEND_BASE_URL}"
echo "Frontend:  http://127.0.0.1:${FRONTEND_PORT}"
echo "Press Ctrl+C to stop."

wait "${backend_pid}" "${frontend_pid}"

