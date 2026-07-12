#!/usr/bin/env bash
# VM 上で Docker Compose (v1: docker-compose) を使いアプリを起動する。
# 環境変数は GitHub Actions Secrets から注入される（vm-deploy.yml 参照）。
# 手動実行: VM で export してから bash scripts/vm-deploy.sh
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/sdp_dev_CommunityComposer}"
GIT_BRANCH="${GIT_BRANCH:-main}"
COMPOSE=(docker-compose)

cd "$REPO_DIR"

echo "==> Repository: $REPO_DIR (branch: $GIT_BRANCH)"

if [[ "${SKIP_GIT_PULL:-0}" != "1" ]]; then
  echo "==> Sync repository to origin/${GIT_BRANCH}"
  git fetch origin "$GIT_BRANCH"
  git checkout "$GIT_BRANCH"
  # VM 上の手編集残留があると pull が失敗するため、追跡ファイルはリモートに合わせる
  git reset --hard "origin/${GIT_BRANCH}"
fi

GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-}"
GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-}"
SECRET_KEY="${SECRET_KEY:-dev-secret-key-change-me-in-production}"
AUTH_ADMIN_SECRET="${AUTH_ADMIN_SECRET:-admin-secret-change-me}"
GOOGLE_HOSTED_DOMAIN="${GOOGLE_HOSTED_DOMAIN:-shibaura-it.ac.jp}"
FLASK_ENV="${FLASK_ENV:-development}"
FLASK_DEBUG="${FLASK_DEBUG:-0}"

_normalize_public_base_url() {
  local value="${1:-}"
  value="${value%/}"
  if [[ "$value" =~ ^(https?://[^/]+)/ ]]; then
    echo "${BASH_REMATCH[1]}"
    return
  fi
  echo "$value"
}

if [[ -n "$PUBLIC_BASE_URL" ]]; then
  PUBLIC_BASE_URL="$(_normalize_public_base_url "$PUBLIC_BASE_URL")"
  GOOGLE_OAUTH_REDIRECT_URI="${GOOGLE_OAUTH_REDIRECT_URI:-${PUBLIC_BASE_URL}/auth/google/callback}"
  GOOGLE_OAUTH_ADMIN_REDIRECT_URI="${GOOGLE_OAUTH_ADMIN_REDIRECT_URI:-${PUBLIC_BASE_URL}/admin/auth/google/callback}"
fi

is_oauth_ready() {
  [[ -n "$GOOGLE_CLIENT_ID" && "$GOOGLE_CLIENT_ID" != "dummy-id" && "$GOOGLE_CLIENT_ID" != "your_google_client_id_here" \
     && -n "$GOOGLE_CLIENT_SECRET" && "$GOOGLE_CLIENT_SECRET" != "dummy" && "$GOOGLE_CLIENT_SECRET" != "your_google_client_secret_here" ]]
}

if [[ -n "${AUTH_MOCK_ENABLED:-}" ]]; then
  echo "==> AUTH_MOCK_ENABLED explicitly set to ${AUTH_MOCK_ENABLED}"
elif is_oauth_ready; then
  AUTH_MOCK_ENABLED="0"
  echo "==> Write .env for VM deploy (Google OAuth enabled)"
else
  AUTH_MOCK_ENABLED="1"
  GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-dummy-id}"
  GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-dummy}"
  echo "==> Write .env for VM deploy (mock auth; set GOOGLE_CLIENT_ID/SECRET for OAuth)"
fi

cat > .env <<EOF
AUTH_MOCK_ENABLED=${AUTH_MOCK_ENABLED}
SECRET_KEY=${SECRET_KEY}
AUTH_ADMIN_SECRET=${AUTH_ADMIN_SECRET}
GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
GOOGLE_HOSTED_DOMAIN=${GOOGLE_HOSTED_DOMAIN}
PUBLIC_BASE_URL=${PUBLIC_BASE_URL}
GOOGLE_OAUTH_REDIRECT_URI=${GOOGLE_OAUTH_REDIRECT_URI:-}
GOOGLE_OAUTH_ADMIN_REDIRECT_URI=${GOOGLE_OAUTH_ADMIN_REDIRECT_URI:-}
FLASK_ENV=${FLASK_ENV}
FLASK_DEBUG=${FLASK_DEBUG}
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
if [[ "$AUTH_MOCK_ENABLED" == "0" ]]; then
  echo "Deploy OK (Google OAuth)."
  echo "  UI:  http://${VM_IP}:8080/login"
  echo "  API: http://${VM_IP}:8000"
  if [[ -n "$PUBLIC_BASE_URL" ]]; then
    echo "  OAuth redirect: ${PUBLIC_BASE_URL}/auth/google/callback"
  else
    echo "  NOTE: Set PUBLIC_BASE_URL (HTTPS) and register redirect URIs in Google Console."
  fi
else
  echo "Deploy OK (mock auth)."
  echo "  UI:  http://${VM_IP}:8080/login"
  echo "  API: http://${VM_IP}:8000"
  echo "  Login: open UI and use email mock login"
fi
