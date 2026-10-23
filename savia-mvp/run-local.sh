#!/usr/bin/env bash
# Run Savia on your own computer. Usage: ./run-local.sh
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] || { echo "Create .env first: cp .env.example .env and fill BOT_TOKEN + ANTHROPIC_API_KEY"; exit 1; }
[ -d node_modules ] || npm install
set -a; . ./.env; set +a
exec npm start
