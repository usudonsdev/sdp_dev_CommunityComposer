#!/usr/bin/env bash
# VM 上で Docker Compose (v1: docker-compose) を使いアプリを起動する。
# 認証はモック（AUTH_MOCK_ENABLED=1）。Google OAuth は後から有効化可能。
# GitHub Actions「Deploy to VM」から実行、または VM で:
#   bash ~/sdp_dev_CommunityComposer/scripts/vm-deploy.sh
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/sdp_dev_CommunityComposer}"
GIT_BRANCH="${GIT_BRANCH:-main}"
COMPOSE=(docker-compose)

cd "$REPO_DIR"

echo "==> Repository: $REPO_DIR (branch: $GIT_BRANCH)"

if [[ "${SKIP_GIT_PULL:-0}" != "1" ]]; then
  echo "==> git pull"
  git fetch origin "$GIT_BRANCH"
  git checkout "$GIT_BRANCH"
  git pull origin "$GIT_BRANCH"
fi

echo "==> Write .env for VM deploy (mock auth enabled)"
cat > .env <<EOF
AUTH_MOCK_ENABLED=1
SECRET_KEY=${SECRET_KEY:-dev-secret-key-change-me-in-production}
GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID:-dummy-id}
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET:-dummy}
FLASK_ENV=development
FLASK_DEBUG=0
EOF

echo "==> Stop and remove old containers"
"${COMPOSE[@]}" down --remove-orphans || true
"${COMPOSE[@]}" rm -f || true
docker ps -aq --filter "name=sdp_dev_communitycomposer" | xargs -r docker rm -f || true

echo "==> Build and start"
"${COMPOSE[@]}" build --no-cache
"${COMPOSE[@]}" up -d --force-recreate

echo "==> Wait for startup"
sleep 5

echo "==> Container status"
"${COMPOSE[@]}" ps

if ! "${COMPOSE[@]}" ps | grep -q "Up"; then
  echo "ERROR: One or more containers are not Up"
  "${COMPOSE[@]}" logs --tail 40
  exit 1
fi

VM_IP="$(hostname -I | awk '{print $1}')"
echo ""
echo "Deploy OK (mock auth)."
echo "  UI:  http://${VM_IP}:8080/login"
echo "  API: http://${VM_IP}:8000"
echo "  Login: open UI and click Google login (uses mock token)"
