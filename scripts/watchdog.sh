#!/usr/bin/env bash
# Watchdog: restart the bot if it is not running. Run every minute via cron.

SERVICE="trading-bot"

if ! systemctl is-active --quiet "$SERVICE"; then
    echo "$(date -Iseconds) $SERVICE is down; restarting" >> /home/ubuntu/watchdog.log
    sudo systemctl restart "$SERVICE"
fi
