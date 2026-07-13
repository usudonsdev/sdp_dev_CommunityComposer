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
SMTP_HOST="${SMTP_HOST:-}"
SMTP_PORT="${SMTP_PORT:-587}"
SMTP_USER="${SMTP_USER:-}"
SMTP_PASSWORD="${SMTP_PASSWORD:-}"
SMTP_FROM="${SMTP_FROM:-}"
SMTP_USE_TLS="${SMTP_USE_TLS:-1}"
MAGIC_LINK_EXPIRE_MINUTES="${MAGIC_LINK_EXPIRE_MINUTES:-15}"

_normalize_public_base_url() {
  local value="${1:-}"
  value="${value%/}"
  if [[ "$value" =~ ^(https?://[^/]+)/ ]]; then
    echo "${BASH_REMATCH[1]}"
    return
  fi
  echo "$value"
}

resolve_docker_dns() {
  if [[ -n "${DOCKER_DNS_1:-}" ]]; then
    echo "==> DOCKER_DNS from environment: ${DOCKER_DNS_1}${DOCKER_DNS_2:+ ${DOCKER_DNS_2}}"
    return
  fi

  local dns_file="/etc/resolv.conf"
  if [[ -f /run/systemd/resolve/resolv.conf ]]; then
    dns_file="/run/systemd/resolve/resolv.conf"
  fi

  local servers=()
  while IFS= read -r ip; do
    [[ -n "$ip" ]] && servers+=("$ip")
  done < <(grep '^nameserver' "$dns_file" 2>/dev/null | awk '{print $2}' | grep -Ev '^127\.' | head -2)

  if [[ ${#servers[@]} -eq 0 ]]; then
    while IFS= read -r ip; do
      [[ -n "$ip" ]] && servers+=("$ip")
    done < <(grep '^nameserver' /etc/resolv.conf 2>/dev/null | awk '{print $2}' | head -2)
  fi

  DOCKER_DNS_1="${servers[0]:-8.8.8.8}"
  DOCKER_DNS_2="${servers[1]:-}"
  echo "==> Docker DNS for web container: ${DOCKER_DNS_1}${DOCKER_DNS_2:+ ${DOCKER_DNS_2}}"
}

write_docker_compose_override() {
  local resolv=""
  if [[ -f /run/systemd/resolve/resolv.conf ]]; then
    resolv="/run/systemd/resolve/resolv.conf"
  elif [[ -f /etc/resolv.conf ]]; then
    resolv="/etc/resolv.conf"
  fi
  if [[ -z "$resolv" ]]; then
    return
  fi
  cat > docker-compose.override.yml <<EOF
services:
  web:
    volumes:
      - ${resolv}:/etc/resolv.conf:ro
EOF
  echo "==> Mount host resolv.conf into web container: ${resolv}"
}

verify_smtp_connectivity() {
  if [[ -z "${SMTP_HOST:-}" ]]; then
    return
  fi
  echo "==> Verify SMTP DNS/TCP from web container"
  if "${COMPOSE[@]}" exec -T web python -c "import os,socket; h=os.environ.get('SMTP_HOST','smtp.gmail.com'); p=int(os.environ.get('SMTP_PORT','587')); print('DNS', socket.gethostbyname(h)); socket.create_connection((h,p), timeout=10); print('SMTP TCP OK')"; then
    echo "==> SMTP connectivity OK"
  else
    echo "WARNING: SMTP connectivity check failed (magic link email may not work on this VM network)"
  fi
}

write_env_file() {
  cat > .env <<EOF
REQUIRE_AUTH_TOKEN=1
AUTH_MOCK_ENABLED=${AUTH_MOCK_ENABLED}
AUTH_MAGIC_LINK_ENABLED=${AUTH_MAGIC_LINK_ENABLED}
AUTH_ADMIN_EMAILS=${AUTH_ADMIN_EMAILS:-adminAL24000@shibaura-it.ac.jp,admin@shibaura-it.ac.jp}
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
SMTP_HOST=${SMTP_HOST}
SMTP_PORT=${SMTP_PORT}
SMTP_USER=${SMTP_USER}
SMTP_PASSWORD=${SMTP_PASSWORD}
SMTP_FROM=${SMTP_FROM}
SMTP_USE_TLS=${SMTP_USE_TLS}
MAGIC_LINK_EXPIRE_MINUTES=${MAGIC_LINK_EXPIRE_MINUTES}
DOCKER_DNS_1=${DOCKER_DNS_1}
EOF
  if [[ -n "${DOCKER_DNS_2:-}" ]]; then
    echo "DOCKER_DNS_2=${DOCKER_DNS_2}" >> .env
  fi
}

sync_oauth_redirect_uris() {
  if [[ -n "$PUBLIC_BASE_URL" ]]; then
    PUBLIC_BASE_URL="$(_normalize_public_base_url "$PUBLIC_BASE_URL")"
    GOOGLE_OAUTH_REDIRECT_URI="${PUBLIC_BASE_URL}/auth/google/callback"
    GOOGLE_OAUTH_ADMIN_REDIRECT_URI="${PUBLIC_BASE_URL}/admin/auth/google/callback"
  fi
}

start_tunnel_and_sync_public_url() {
  echo "==> Start Cloudflare tunnel (profile: tunnel)"
  "${COMPOSE[@]}" --profile tunnel up -d --force-recreate tunnel
  sleep 8

  local tunnel_url=""
  tunnel_url="$("${COMPOSE[@]}" logs tunnel 2>&1 | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1 || true)"
  if [[ -z "$tunnel_url" ]]; then
    echo "WARNING: Could not read trycloudflare URL from tunnel logs."
    echo "         Run: docker-compose --profile tunnel logs tunnel"
    return 1
  fi

  echo "==> Live tunnel URL: ${tunnel_url}"
  if [[ "$PUBLIC_BASE_URL" != "$tunnel_url" ]]; then
    echo "==> Sync PUBLIC_BASE_URL to live tunnel URL (trycloudflare URL changes on restart)"
    PUBLIC_BASE_URL="$tunnel_url"
    sync_oauth_redirect_uris
    write_env_file
    echo "==> Recreate ui container with updated OAuth redirect URIs"
    "${COMPOSE[@]}" up -d --force-recreate ui
    sleep 3
  fi
  return 0
}

if [[ -n "$PUBLIC_BASE_URL" ]]; then
  sync_oauth_redirect_uris
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

if [[ "$AUTH_MOCK_ENABLED" == "1" && -z "$PUBLIC_BASE_URL" && -n "$SMTP_HOST" ]]; then
  PUBLIC_BASE_URL="http://$(hostname -I | awk '{print $1}'):8080"
  echo "==> PUBLIC_BASE_URL for magic links: ${PUBLIC_BASE_URL}"
fi

if [[ "$AUTH_MOCK_ENABLED" == "1" && -z "${AUTH_MAGIC_LINK_ENABLED:-}" ]]; then
  AUTH_MAGIC_LINK_ENABLED="0"
  echo "==> AUTH_MAGIC_LINK_ENABLED=0 (instant @shibaura-it.ac.jp email login on VM)"
fi

resolve_docker_dns

write_env_file
write_docker_compose_override

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

if [[ "$AUTH_MOCK_ENABLED" == "0" ]]; then
  start_tunnel_and_sync_public_url || true
fi

if [[ -n "${SMTP_HOST:-}" && -n "${SMTP_FROM:-}" && "${AUTH_MAGIC_LINK_ENABLED:-0}" == "1" ]]; then
  verify_smtp_connectivity || true
fi

VM_IP="$(hostname -I | awk '{print $1}')"
echo ""
if [[ "$AUTH_MOCK_ENABLED" == "0" ]]; then
  echo "Deploy OK (Google OAuth)."
  echo "  UI (VPN):  http://${VM_IP}:8080/login"
  echo "  API (VPN): http://${VM_IP}:8000"
  if [[ -n "$PUBLIC_BASE_URL" ]]; then
    echo "  Public UI: ${PUBLIC_BASE_URL}/login"
    echo "  OAuth redirect: ${PUBLIC_BASE_URL}/auth/google/callback"
    if [[ "$PUBLIC_BASE_URL" == *trycloudflare.com* ]]; then
      echo "  NOTE: Register the OAuth redirect URI above in Google Console."
      echo "        trycloudflare URL may change when tunnel restarts."
    fi
  else
    echo "  NOTE: Set PUBLIC_BASE_URL (HTTPS) and register redirect URIs in Google Console."
  fi
else
  if [[ "${AUTH_MAGIC_LINK_ENABLED:-0}" == "1" && -n "$SMTP_HOST" && -n "$SMTP_FROM" ]]; then
    echo "Deploy OK (magic link auth)."
    echo "  UI:  http://${VM_IP}:8080/login"
    echo "  API: http://${VM_IP}:8000"
    echo "  Login: enter email on UI, then open the link sent by mail"
    if [[ -n "$PUBLIC_BASE_URL" ]]; then
      echo "  Magic link base: ${PUBLIC_BASE_URL}"
    fi
  elif [[ "$AUTH_MOCK_ENABLED" == "1" ]]; then
    echo "Deploy OK (instant email login)."
    echo "  UI:  http://${VM_IP}:8080/login"
    echo "  API: http://${VM_IP}:8000"
    echo "  Login: enter @shibaura-it.ac.jp email to register and sign in"
  else
    echo "Deploy OK (mock auth)."
    echo "  UI:  http://${VM_IP}:8080/login"
    echo "  API: http://${VM_IP}:8000"
    echo "  Login: open UI and use email mock login"
    echo "  NOTE: Set SMTP_* secrets for magic link email auth on VM"
  fi
fi
