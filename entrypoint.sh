#!/usr/bin/env sh
set -e
if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
  echo "Waiting for postgres at $DB_HOST:$DB_PORT..."
  while ! nc -z "$DB_HOST" "$DB_PORT"; do
    sleep 1
  done
fi
python manage.py collectstatic --noinput
python manage.py migrate --noinput
exec "$@"
