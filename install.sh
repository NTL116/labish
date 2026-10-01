#!/usr/bin/env bash
#
# Labish single-command installer for a fresh Debian host.
#
#   curl -fsSL https://<git-host>/<owner>/labish/raw/main/install.sh | sudo bash
#
# Thin wrapper only (see the "INSTALLER SYNC & COMPLIANCE BOUNDARY" rule in
# AGENTS.md): it verifies the host, fetches the repository, and hands off to
# the real provisioning engine, apps/api/app/setup.py, non-interactively.
# Re-running it on a provisioned host is a safe no-op/upgrade.
#
# Configuration (environment variables):
#   LABISH_REPO_URL     Git remote to clone (default: GitHub NTL116/labish).
#   LABISH_INSTALL_DIR  Checkout location (default: /opt/labish).
#   LABISH_BRANCH       Branch to install (default: main).
#   LABISH_SERVER_NAME  nginx server_name (default: "_").
#   LABISH_SITE_URL     Public origin for NEXT_PUBLIC_SITE_URL.
#   LABISH_SERVICE_USER Account the services run as (default: auto-detect).
#
# Extra arguments are forwarded to setup.py (e.g. --skip-systemd).

set -euo pipefail

REPO_URL="${LABISH_REPO_URL:-https://github.com/NTL116/labish.git}"
INSTALL_DIR="${LABISH_INSTALL_DIR:-/opt/labish}"
BRANCH="${LABISH_BRANCH:-main}"

log()  { echo "[install] $*"; }
fail() { echo "[install][error] $*" >&2; exit 1; }

# --- Host verification -----------------------------------------------------
[ "$(uname -s)" = "Linux" ] || fail "Labish installs on Linux (Debian) only."
command -v apt-get >/dev/null 2>&1 \
  || fail "apt-get not found; this installer supports Debian-based hosts."
if [ "$(id -u)" -ne 0 ]; then
  fail "Run as root: curl -fsSL .../install.sh | sudo bash"
fi

# --- Bootstrap prerequisites (git, curl, python) ----------------------------
export DEBIAN_FRONTEND=noninteractive
missing=""
for bin in git curl python3; do
  command -v "$bin" >/dev/null 2>&1 || missing="$missing $bin"
done
# python3-venv has no probe binary; let apt decide whether it is needed.
log "Installing base prerequisites via apt..."
apt-get update -qq
# shellcheck disable=SC2086
apt-get install -y -qq git curl ca-certificates python3 python3-venv python3-pip ${missing}

# --- Fetch (or update) the repository ---------------------------------------
if [ -f "${BASH_SOURCE[0]:-}" ] && [ -f "$(dirname "${BASH_SOURCE[0]}")/apps/api/app/setup.py" ]; then
  # Running from inside an existing checkout (manual/CI invocation).
  INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  log "Using existing repository checkout: ${INSTALL_DIR}"
elif [ -d "${INSTALL_DIR}/.git" ]; then
  log "Updating existing checkout in ${INSTALL_DIR} (branch ${BRANCH})..."
  git -C "${INSTALL_DIR}" fetch origin "${BRANCH}"
  git -C "${INSTALL_DIR}" checkout "${BRANCH}"
  git -C "${INSTALL_DIR}" pull --ff-only origin "${BRANCH}"
else
  log "Cloning ${REPO_URL} (branch ${BRANCH}) into ${INSTALL_DIR}..."
  git clone --branch "${BRANCH}" --depth 1 "${REPO_URL}" "${INSTALL_DIR}"
fi

# --- Hand off to the provisioning engine ------------------------------------
log "Handing off to apps/api/app/setup.py --yes ..."
exec python3 "${INSTALL_DIR}/apps/api/app/setup.py" --yes "$@"
