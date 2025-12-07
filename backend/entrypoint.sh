#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.5
done
echo "PostgreSQL started"

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Load ingredients if the database is empty
echo "Loading ingredients data..."
python manage.py load_ingredients --path /app/data/ingredients.json || true

# Start gunicorn
echo "Starting gunicorn..."
exec gunicorn foodgram.wsgi:application --bind 0:8000

