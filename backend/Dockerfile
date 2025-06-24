FROM python:3.12-slim

# системні пакети
RUN apt-get update -y \
 && apt-get install -y --no-install-recommends gcc \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# Переконайтесь, що в requirements.txt є uvicorn[standard]:
# uvicorn[standard]>=0.23.0

COPY . .

# зберемо статику (якщо потрібно)
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Викликаємо ASGI-аплікацію в config/asgi.py
CMD ["uvicorn", "config.asgi:application", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--reload", \
     "--log-level", "debug"]
