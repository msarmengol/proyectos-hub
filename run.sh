#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

echo "=========================================================="
echo "⚡ Iniciando ProjectHub en http://localhost:$PORT"
echo "=========================================================="

"$DIR/venv/bin/uvicorn" app.main:app --host "$HOST" --port "$PORT" --reload
