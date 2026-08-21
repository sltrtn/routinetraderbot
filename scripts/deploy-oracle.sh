#!/usr/bin/env bash
# Deploy RoutineTraderBot to an Oracle Cloud Always Free VM.
#
# Usage:
#   ./scripts/deploy-oracle.sh ubuntu@<VM_IP> [ssh_key_path]
#
# What it does:
#   1. rsyncs the project to /home/ubuntu/routinetraderbot
#   2. installs Python deps into a venv on the VM
#   3. installs the systemd service
#   4. restarts and enables the bot
#
# NOTE: .env is NOT synced by default. Copy it manually or pass SYNC_ENV=1.

set -euo pipefail

REMOTE="${1:?Usage: $0 ubuntu@VM_IP [ssh_key_path]}"
SSH_KEY="${2:-}"
PROJECT_DIR="/home/mad/trading-bot"
REMOTE_DIR="/home/ubuntu/routinetraderbot"

SSH_OPTS="-o StrictHostKeyChecking=accept-new"
[ -n "$SSH_KEY" ] && SSH_OPTS="$SSH_OPTS -i $SSH_KEY"

echo "==> Syncing project to $REMOTE:$REMOTE_DIR"
rsync -avz --delete \
  --exclude '.venv' \
  --exclude '.git' \
  --exclude 'data/bot.db*' \
  --exclude '*.log' \
  ${SYNC_ENV:+} \
  $( [ "${SYNC_ENV:-0}" = "1" ] && echo "" || echo "--exclude .env" ) \
  -e "ssh $SSH_OPTS" \
  "$PROJECT_DIR/" "$REMOTE:$REMOTE_DIR/"

echo "==> Provisioning VM (python, venv, deps)"
ssh $SSH_OPTS "$REMOTE" bash -s <<'EOF'
set -euo pipefail
cd /home/ubuntu/routinetraderbot
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt --quiet

# Ensure data dir exists
mkdir -p data

# Install systemd service
sudo cp systemd/trading-bot.service /etc/systemd/system/
sudo sed -i 's|/home/ubuntu/trading-bot|/home/ubuntu/routinetraderbot|g' /etc/systemd/system/trading-bot.service
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
EOF

if [ "${SYNC_ENV:-0}" = "1" ]; then
  echo "==> Synced .env (SYNC_ENV=1)"
else
  echo "==> .env NOT synced. Copy it manually:"
  echo "    scp $SSH_KEY_OPT $PROJECT_DIR/.env $REMOTE:$REMOTE_DIR/.env"
fi

echo "==> Restarting service"
ssh $SSH_OPTS "$REMOTE" sudo systemctl restart trading-bot

echo "==> Status"
ssh $SSH_OPTS "$REMOTE" sudo systemctl status trading-bot --no-pager | head -15

echo ""
echo "Done. Follow logs with:"
echo "  ssh $SSH_OPTS $REMOTE journalctl -u trading-bot -f"
