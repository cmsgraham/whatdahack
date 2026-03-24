#!/bin/bash
# =============================================================================
# migrate.sh — Move CTFd to a new server
#
# Usage:
#   ./scripts/migrate.sh <NEW_SERVER_IP> [SSH_KEY]
#
# Examples:
#   ./scripts/migrate.sh 192.0.2.100
#   ./scripts/migrate.sh 192.0.2.100 ~/.ssh/linode
#
# What this script does:
#   1. Dumps the MariaDB database from the current server
#   2. Rsyncs uploads, DKIM key, and SSL certs to the new server
#   3. Bootstraps the new server (Docker, git clone)
#   4. Restores the database on the new server
#   5. Starts all containers on the new server
#
# After this script completes:
#   - Update your DNS A record to point to NEW_SERVER_IP
#   - Verify the site is up before decommissioning the old server
# =============================================================================

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────
OLD_SERVER="cmsgraham@172.233.162.57"
NEW_SERVER_IP="${1:?Usage: $0 <NEW_SERVER_IP> [SSH_KEY]}"
NEW_SERVER_USER="${NEW_SERVER_USER:-root}"
NEW_SERVER="${NEW_SERVER_USER}@${NEW_SERVER_IP}"
SSH_KEY="${2:-~/.ssh/linode}"
REPO="git@github.com:cmsgraham/whatdahack.git"
REMOTE_PATH="/opt/CTFd"
COMPOSE="sudo docker compose -f ${REMOTE_PATH}/docker-compose.yml"

OLD_SSH="ssh -F /dev/null -i ${SSH_KEY} -o IdentitiesOnly=yes -o IdentityAgent=none -o StrictHostKeyChecking=no"
NEW_SSH="ssh -F /dev/null -i ${SSH_KEY} -o IdentitiesOnly=yes -o IdentityAgent=none -o StrictHostKeyChecking=no"
RSYNC="rsync -az --progress -e \"ssh -F /dev/null -i ${SSH_KEY} -o IdentitiesOnly=yes -o IdentityAgent=none -o StrictHostKeyChecking=no\""

# ── Helpers ──────────────────────────────────────────────────────────────────
log() { echo -e "\n\033[1;34m[$(date +%H:%M:%S)] $*\033[0m"; }
ok()  { echo -e "\033[0;32m  ✓ $*\033[0m"; }
err() { echo -e "\033[0;31m  ✗ $*\033[0m"; exit 1; }

# ── Step 1: Dump database from old server ────────────────────────────────────
log "Step 1/5 — Dumping database from ${OLD_SERVER}"

$OLD_SSH "${OLD_SERVER}" "
  ${COMPOSE} exec -T db mysqldump \
    -uctfd -pctfd ctfd \
    --single-transaction --routines --triggers \
    > /tmp/ctfd_migrate.sql
  echo 'rows:' \$(wc -l < /tmp/ctfd_migrate.sql)
"
ok "Database dumped to /tmp/ctfd_migrate.sql on old server"

# ── Step 2: Transfer all data to new server ───────────────────────────────────
log "Step 2/5 — Transferring data to ${NEW_SERVER}"

# Ensure destination dirs exist
$NEW_SSH "${NEW_SERVER}" "mkdir -p /tmp/ctfd_migration /var/ctfd_uploads"

# DB dump
eval ${RSYNC} "${OLD_SERVER}:/tmp/ctfd_migrate.sql" "${NEW_SERVER}:/tmp/ctfd_migration/ctfd.sql"
ok "DB dump transferred"

# Uploads (user files, social images, etc.)
eval ${RSYNC} --rsync-path="sudo rsync" \
  "${OLD_SERVER}:${REMOTE_PATH}/.data/CTFd/uploads/" \
  "${NEW_SERVER}:/tmp/ctfd_migration/uploads/"
ok "Uploads transferred"

# DKIM private key (not in git)
eval ${RSYNC} --rsync-path="sudo rsync" \
  "${OLD_SERVER}:${REMOTE_PATH}/conf/exim4/dkim.private" \
  "${NEW_SERVER}:/tmp/ctfd_migration/dkim.private"
ok "DKIM key transferred"

# Let's Encrypt certs
eval ${RSYNC} --rsync-path="sudo rsync" \
  "${OLD_SERVER}:/etc/letsencrypt/" \
  "${NEW_SERVER}:/tmp/ctfd_migration/letsencrypt/"
ok "SSL certs transferred"

# ── Step 3: Bootstrap new server ─────────────────────────────────────────────
log "Step 3/5 — Bootstrapping new server ${NEW_SERVER}"

$NEW_SSH "${NEW_SERVER}" "
  set -e
  export DEBIAN_FRONTEND=noninteractive

  echo '--- Installing dependencies ---'
  apt-get update -y -q
  apt-get install -y -q git curl ca-certificates gnupg lsb-release rsync

  echo '--- Installing Docker ---'
  if ! command -v docker &>/dev/null; then
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \$(lsb_release -cs) stable\" \
      | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -y -q
    apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    echo 'Docker installed'
  else
    echo 'Docker already installed'
  fi

  echo '--- Cloning repo ---'
  if [ -d ${REMOTE_PATH} ]; then
    git -C ${REMOTE_PATH} pull
  else
    git clone ${REPO} ${REMOTE_PATH}
  fi

  echo '--- Placing data files ---'
  mkdir -p ${REMOTE_PATH}/.data/CTFd/uploads ${REMOTE_PATH}/.data/CTFd/logs ${REMOTE_PATH}/.data/mysql ${REMOTE_PATH}/.data/redis
  cp -r /tmp/ctfd_migration/uploads/. ${REMOTE_PATH}/.data/CTFd/uploads/ 2>/dev/null || true
  cp /tmp/ctfd_migration/dkim.private ${REMOTE_PATH}/conf/exim4/dkim.private

  echo '--- Placing SSL certs ---'
  mkdir -p /etc/letsencrypt
  cp -r /tmp/ctfd_migration/letsencrypt/. /etc/letsencrypt/ 2>/dev/null || true

  echo 'Bootstrap complete'
"
ok "New server bootstrapped"

# ── Step 4: Restore database ──────────────────────────────────────────────────
log "Step 4/5 — Restoring database on ${NEW_SERVER}"

$NEW_SSH "${NEW_SERVER}" "
  set -e
  cd ${REMOTE_PATH}

  echo '--- Starting DB container only ---'
  docker compose -f ${REMOTE_PATH}/docker-compose.yml up -d db
  echo 'Waiting for MariaDB to be ready...'
  for i in \$(seq 1 30); do
    docker compose -f ${REMOTE_PATH}/docker-compose.yml exec -T db mysqladmin ping -uctfd -pctfd --silent 2>/dev/null && break
    sleep 2
  done

  echo '--- Restoring dump ---'
  docker compose -f ${REMOTE_PATH}/docker-compose.yml exec -T db \
    mysql -uctfd -pctfd ctfd < /tmp/ctfd_migration/ctfd.sql
  echo 'Database restored'
"
ok "Database restored"

# ── Step 5: Start all services ────────────────────────────────────────────────
log "Step 5/5 — Starting all services on ${NEW_SERVER}"

$NEW_SSH "${NEW_SERVER}" "
  cd ${REMOTE_PATH}
  docker compose -f ${REMOTE_PATH}/docker-compose.yml up -d --build
  sleep 5
  docker compose -f ${REMOTE_PATH}/docker-compose.yml ps
"
ok "All services started"

# ── Done ──────────────────────────────────────────────────────────────────────
log "Migration complete!"
echo ""
echo "  New server: https://${NEW_SERVER_IP}"
echo ""
echo "  Next steps:"
echo "    1. Verify the site loads correctly at https://${NEW_SERVER_IP}"
echo "    2. Update your DNS A record: whatdahack.com → ${NEW_SERVER_IP}"
echo "    3. Wait for DNS TTL to expire before decommissioning old server"
echo "    4. Submit Proofpoint unblock for new IP:"
echo "       https://ipcheck.proofpoint.com/?ip=${NEW_SERVER_IP}"
echo ""
