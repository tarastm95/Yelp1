#!/usr/bin/env python3
"""
Створення Django міграцій для нових моделей SystemErrorLog та SystemHealthMetric
"""

# Команди для виконання на сервері:

commands = [
    "cd /var/www/yelp/backend/",
    "docker compose exec backend python manage.py makemigrations webhooks",
    "docker compose exec backend python manage.py migrate",
    "docker compose restart backend worker scheduler",
]

print("🚀 Команди для створення міграцій на сервері:")
print("=" * 60)
for cmd in commands:
    print(f"$ {cmd}")

print("\n📝 Примітка:")
print("Ці команди потрібно виконати на сервері після git pull")
