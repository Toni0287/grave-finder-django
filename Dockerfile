# Small official Python image
FROM python:3.12-slim

# Print output straight away and don't write .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_DEBUG=false \
    DJANGO_DB_PATH=/app/data/db.sqlite3

WORKDIR /app

# Install dependencies first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput && mkdir -p /app/data

EXPOSE 8000

# Migrate, load the demo data (skipped if already there), then serve
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_graves && python manage.py seed_memorials && gunicorn gravefinder.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
