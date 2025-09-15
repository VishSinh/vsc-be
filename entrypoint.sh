#!/usr/bin/env sh
set -e
if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
  echo "Waiting for postgres at $DB_HOST:$DB_PORT..."
  while ! nc -z "$DB_HOST" "$DB_PORT"; do
    sleep 1
  done
fi
# Ensure writable volumes then drop privileges
mkdir -p /app/media /app/staticfiles
chown -R appuser:appuser /app/media /app/staticfiles || true

su_exec="gosu appuser"

$su_exec python manage.py collectstatic --noinput
$su_exec python manage.py migrate --noinput
if [ "$#" -eq 1 ]; then
  exec gosu appuser sh -lc "$1"
else
  exec gosu appuser "$@"
fi
