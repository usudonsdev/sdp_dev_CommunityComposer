#!/usr/bin/env bash
# ローカル開発用: localhost の OAuth リダイレクトで起動
set -euo pipefail

cd "$(dirname "$0")/.."
docker compose -f compose.yaml -f compose.local.yaml up -d --build "$@"

echo ""
echo "Local dev started."
echo "  UI:  http://localhost:8080/login"
echo "  API: http://localhost:8000"
echo "  OAuth redirect: http://localhost:8080/auth/google/callback"
