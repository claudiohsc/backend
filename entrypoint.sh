#!/bin/sh

set -e

echo 'Waiting for database...'
until python -c "import psycopg2; psycopg2.connect(host='$DB_HOSTNAME', port='${DB_PORT:-5432}', dbname='$DB_NAME', user='$DB_USERNAME', password='$DB_PASSWORD')" 2>/dev/null; do
  echo 'Database unavailable, retrying in 2s...'
  sleep 2
done
echo 'Database ready.'

echo 'Migrating database...'
python manage.py migrate --noinput

echo 'Creating superuser...'
python manage.py initadmin

if [ "$DEBUG" = "True" ] || [ "$DEBUG" = "true" ] || [ "$DEBUG" = "1" ]; then
    exec python manage.py runserver 0.0.0.0:${PORT:-8000}
fi

python manage.py collectstatic --noinput
exec gunicorn core.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3