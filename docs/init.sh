#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo "=== 可信人格记忆Agent Real Multimodal Provider harness ==="

if command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "Python is required for JSON validation but was not found in PATH."
  exit 1
fi

required_files=(
  "AGENTS.md"
  "backend/.dockerignore"
  "backend/Dockerfile"
  "backend/docker-entrypoint.sh"
  "frontend/.dockerignore"
  "frontend/Dockerfile"
  "docker-compose.yml"
  "docs/README.md"
  "docs/可信人格记忆Agent_mvp_prd.md"
  "docs/feature-list.json"
  "docs/progress.md"
  "docs/prd-checklist.md"
  "docs/平台说明.md"
  "docs/init.sh"
)

echo "=== Required harness files ==="
for file in "${required_files[@]}"; do
  if [ ! -f "$file" ]; then
    echo "Missing required file: $file"
    exit 1
  fi
  echo "OK: $file"
done

echo "=== JSON validation ==="
"$PYTHON_BIN" -m json.tool docs/feature-list.json >/dev/null
echo "OK: docs/feature-list.json"

echo "=== Backend tests ==="
if "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import pytest  # noqa: F401
PY
then
  "$PYTHON_BIN" -m pytest backend/tests -q
else
  echo "SKIP: pytest is not installed for $PYTHON_BIN. Install backend requirements before running backend tests."
fi

echo "=== Frontend checks ==="
if command -v npm.cmd >/dev/null 2>&1; then
  NPM_BIN="npm.cmd"
elif command -v npm >/dev/null 2>&1; then
  NPM_BIN="npm"
else
  NPM_BIN=""
fi

if [ -z "$NPM_BIN" ]; then
  echo "SKIP: npm was not found. Install Node.js before running frontend checks."
elif [ ! -d "frontend/node_modules" ]; then
  echo "SKIP: frontend/node_modules is missing. Run npm.cmd --prefix frontend install on Windows PowerShell, or npm --prefix frontend install where npm.cmd is unavailable."
else
  "$NPM_BIN" --prefix frontend run test
  "$NPM_BIN" --prefix frontend run lint
  "$NPM_BIN" --prefix frontend run build
fi

echo "=== Docker Compose config ==="
if docker compose version >/dev/null 2>&1; then
  docker compose config >/dev/null
  echo "OK: docker compose config"
else
  echo "SKIP: docker compose is not available. Install Docker Compose before validating compose configuration."
fi

echo "=== Optional real multimodal smoke ==="
echo "Manual only: python backend/scripts/real_multimodal_smoke.py --sample-mode public --backend-url http://localhost:8000"

echo "=== Real Multimodal Provider harness complete ==="
