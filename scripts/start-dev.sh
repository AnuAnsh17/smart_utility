#!/usr/bin/env bash
#
# Start the Smart Utility backend and frontend together.
#
# Both processes stay in the foreground of this script; Ctrl-C stops the pair.
# Everything runs on loopback — no document ever leaves this machine.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
VENV="$BACKEND/.venv"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "error: no virtualenv at $VENV" >&2
  echo "  python3 -m venv backend/.venv" >&2
  echo "  backend/.venv/bin/pip install -r backend/requirements.txt" >&2
  exit 1
fi

if [[ ! -d "$ROOT/node_modules" ]]; then
  echo "error: node_modules is missing — run 'npm install' first" >&2
  exit 1
fi

if ! command -v tesseract >/dev/null 2>&1; then
  echo "warning: tesseract is not on PATH; OCR will report unavailable" >&2
fi

PIDS=()
cleanup() {
  trap - INT TERM EXIT
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "backend  -> http://$BACKEND_HOST:$BACKEND_PORT"
(
  cd "$BACKEND"
  exec "$VENV/bin/python" -m uvicorn app.main:app \
    --host "$BACKEND_HOST" --port "$BACKEND_PORT"
) &
PIDS+=("$!")

echo "frontend -> http://localhost:$FRONTEND_PORT"
(
  cd "$ROOT"
  exec npm run dev -- --port "$FRONTEND_PORT"
) &
PIDS+=("$!")

wait -n
