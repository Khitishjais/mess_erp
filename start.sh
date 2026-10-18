#!/bin/bash
set -e
python manage.py migrate --noinput          # creates / updates the tables in your hosted PostgreSQL
python manage.py createcachetable           # shared table for login lock-out counters (all workers see the same count)
python manage.py ensure_owner               # first owner from the OWNER_* secrets (skipped if one exists)
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-7860} --workers 1 --threads 4 --timeout 120 --access-logfile - 
