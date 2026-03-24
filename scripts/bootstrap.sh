#!/bin/bash
# =============================================================================
# bootstrap.sh — Set up CTFd on a fresh server from scratch
#
# Usage (run as root or with sudo):
#   curl -fsSL https://raw.githubusercontent.com/cmsgraham/whatdahack/master/scripts/bootstrap.sh | bash
#   -- or --
#   bash scripts/bootstrap.sh
#
# What this does:
#   1. Installs Docker + Docker Compose
#   2. Clones the whatdahack repo to /opt/CTFd
#   3. Creates required data directories with correct permissions
#   4. Hardens SSH and installs fail2ban
#   5. Prints next steps (DKIM key, SSL, DNS)
#
# NOTE: This script sets up the infrastructure only.
#       For migrating an existing server, use scripts/migrate.sh instead.
# =============================================================================

set -euo pipefail

REPO="git@github.com:cmsgraham/whatdahack.git"
INSTALL_DIR="/opt/CTFd"

log() { echo -e "\n\033[1;34m[$(date +%H:%M:%S)] $*\033[0m"; }
ok()  { echo -e "\033[0;32m  ✓ $*\033[0m"; }

# ── Step 1: System packages ───────────────────────────────────────────────────
log "Step 1/5 — Installing system dependencies"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y -q
apt-get install -y -q \
  git curl ca-certificates gnupg lsb-release \
  rsync fail2ban ufw
ok "System packages installed"

# ── Step 2: Docker ─────────────────────────────────────────────────────────────
log "Step 2/5 — Installing Docker"
if ! command -v docker &>/dev/null; then
  mkdir -p /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null
  apt-get update -y -q
  apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable docker
  systemctl start docker
  ok "Docker installed"
else
  ok "Docker already installed"
fi

# ── Step 3: Clone repo ────────────────────────────────────────────────────────
log "Step 3/5 — Cloning repo to ${INSTALL_DIR}"
if [ -d "${INSTALL_DIR}/.git" ]; then
  git -C "${INSTALL_DIR}" pull
  ok "Repo updated"
else
  git clone "${REPO}" "${INSTALL_DIR}"
  ok "Repo cloned"
fi

# ── Step 4: Create data directories ──────────────────────────────────────────
log "Step 4/5 — Creating data directories"
mkdir -p \
  "${INSTALL_DIR}/.data/CTFd/uploads" \
  "${INSTALL_DIR}/.data/CTFd/logs" \
  "${INSTALL_DIR}/.data/mysql" \
  "${INSTALL_DIR}/.data/redis"
# Uploads must be writable by container user (uid 1001)
chown -R 1001:1001 "${INSTALL_DIR}/.data/CTFd/uploads" "${INSTALL_DIR}/.data/CTFd/logs"
ok "Data directories created"

# ── Step 5: Harden SSH + firewall ────────────────────────────────────────────
log "Step 5/5 — Hardening SSH and firewall"

# fail2ban
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled  = true
port     = ssh
logpath  = %(sshd_log)s
backend  = systemd
maxretry = 3
bantime  = 24h

[nginx-http-auth]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/error.log
EOF
systemctl enable fail2ban
systemctl restart fail2ban

# UFW: allow SSH, HTTP, HTTPS only
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable
ok "Firewall and fail2ban configured"

# SSH hardening
sed -i 's/^X11Forwarding yes/X11Forwarding no/' /etc/ssh/sshd_config
grep -q '^LoginGraceTime'     /etc/ssh/sshd_config || echo 'LoginGraceTime 30'      >> /etc/ssh/sshd_config
grep -q '^MaxAuthTries'       /etc/ssh/sshd_config || echo 'MaxAuthTries 3'         >> /etc/ssh/sshd_config
grep -q '^ClientAliveInterval' /etc/ssh/sshd_config || echo 'ClientAliveInterval 300' >> /etc/ssh/sshd_config
grep -q '^ClientAliveCountMax' /etc/ssh/sshd_config || echo 'ClientAliveCountMax 2'  >> /etc/ssh/sshd_config
sshd -t && systemctl reload sshd
ok "SSH hardened"

# ── Done — print next steps ───────────────────────────────────────────────────
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "<this-server-ip>")

echo ""
echo "============================================================"
echo "  Bootstrap complete!"
echo "  Server IP: ${SERVER_IP}"
echo "============================================================"
echo ""
echo "  REQUIRED MANUAL STEPS before starting services:"
echo ""
echo "  1) Copy the DKIM private key (NOT in git):"
echo "     scp conf/exim4/dkim.private ${SERVER_IP}:${INSTALL_DIR}/conf/exim4/dkim.private"
echo ""
echo "  2) Obtain SSL certificate for whatdahack.com:"
echo "     apt-get install certbot"
echo "     certbot certonly --standalone -d whatdahack.com -d www.whatdahack.com"
echo ""
echo "  3) Point DNS A record: whatdahack.com → ${SERVER_IP}"
echo ""
echo "  4) Start all services:"
echo "     docker compose -f ${INSTALL_DIR}/docker-compose.yml up -d --build"
echo ""
echo "  5) Submit Proofpoint unblock for new IP:"
echo "     https://ipcheck.proofpoint.com/?ip=${SERVER_IP}"
echo ""
echo "  For migrating data from an existing server, use:"
echo "     ./scripts/migrate.sh ${SERVER_IP}"
echo ""
