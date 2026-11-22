#!/bin/sh
# Daily backup. Cron example (as root):  0 2 * * * /opt/gps_notifier/deploy/backup.sh
set -e
DEST=/var/backups/gps; mkdir -p "$DEST"; STAMP=$(date +%F)
mysqldump --single-transaction gps_notifier | gzip > "$DEST/db-$STAMP.sql.gz"
cp /opt/gps_notifier/sessions/main.session "$DEST/session-$STAMP.session" 2>/dev/null || true
chmod 600 "$DEST"/*
find "$DEST" -type f -mtime +14 -delete       # keep 14 days
