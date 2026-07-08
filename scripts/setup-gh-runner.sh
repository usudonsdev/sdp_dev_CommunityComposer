#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: bash scripts/setup-gh-runner.sh <runner-token> [runner-dir]"
  echo "Example: bash scripts/setup-gh-runner.sh TOKEN123 ~/actions-runner"
  exit 1
fi

REPO_URL="https://github.com/usudonsdev/sdp_dev_CommunityComposer"
REPO_DIR="${REPO_DIR:-$HOME/sdp_dev_CommunityComposer}"
RUNNER_TOKEN="$1"
RUNNER_DIR="${2:-$HOME/actions-runner}"
RUNNER_VERSION="2.335.1"
RUNNER_ARCHIVE="actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
RUNNER_DOWNLOAD_URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${RUNNER_ARCHIVE}"
RUNNER_SHA256="4ef2f25285f0ae4477f1fe1e346db76d2f3ebf03824e2ddd1973a2819bf6c8cf"

mkdir -p "${RUNNER_DIR}"
cd "${RUNNER_DIR}"

if [[ ! -f "${RUNNER_ARCHIVE}" ]]; then
  echo "==> Download runner package"
  curl -o "${RUNNER_ARCHIVE}" -L "${RUNNER_DOWNLOAD_URL}"
fi

echo "==> Verify archive hash"
echo "${RUNNER_SHA256}  ${RUNNER_ARCHIVE}" | sha256sum -c

if [[ ! -x "./config.sh" ]]; then
  echo "==> Extract runner package"
  tar xzf "./${RUNNER_ARCHIVE}"
fi

if [[ -f ".runner" ]]; then
  echo "==> Runner already configured in ${RUNNER_DIR}"
else
  echo "==> Configure runner"
  ./config.sh --url "${REPO_URL}" --token "${RUNNER_TOKEN}"
fi

echo "==> Install and start runner service"
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status

if [[ ! -d "${REPO_DIR}/.git" ]]; then
  echo "==> Clone application repository to ${REPO_DIR}"
  git clone "${REPO_URL}" "${REPO_DIR}"
else
  echo "==> Application repository already exists at ${REPO_DIR}"
fi
