#!/bin/bash

echo "🚀 Налаштування Grafana Loki для пошуку логів..."

# Перевіряємо чи встановлений Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не знайдено!"
    exit 1
fi

# Запускаємо сервіси
echo "📦 Запуск Loki, Promtail та Grafana..."
docker-compose up -d loki promtail grafana

# Очікуємо запуску сервісів
echo "⏳ Очікування запуску сервісів (30 секунд)..."
sleep 30

# Перевіряємо статус
echo "🔍 Перевірка статусу сервісів..."
docker-compose ps | grep -E "(loki|promtail|grafana)"

# Перевіряємо чи працює Loki
echo "🧪 Тестування Loki API..."
if curl -s http://localhost:3100/ready > /dev/null; then
    echo "✅ Loki працює!"
else
    echo "❌ Loki не відповідає"
fi

# Перевіряємо чи працює Grafana
echo "🧪 Тестування Grafana..."
if curl -s http://localhost:3030 > /dev/null; then
    echo "✅ Grafana працює!"
    echo "🌐 Відкрийте браузер: http://46.62.139.177:3030"
    echo "🔑 Логін: admin / Пароль: admin123"
else
    echo "❌ Grafana не відповідає"
fi

echo ""
echo "📋 Корисні команди:"
echo "  Логи Loki:     docker-compose logs -f loki"
echo "  Логи Promtail: docker-compose logs -f promtail"
echo "  Логи Grafana:  docker-compose logs -f grafana"
echo "  Зупинити:      docker-compose stop loki promtail grafana"
echo ""
echo "🔍 Приклади пошуку в Grafana:"
echo "  Всі логи:          {container_name=~\".*backend.*\"}"
echo "  Пошук по Lead ID:  {container_name=~\".*backend.*\"} |~ \"t8BmZdUiv9PNZWjwCuQNw\""
echo "  Тільки помилки:    {container_name=~\".*backend.*\"} |~ \"(?i)(error|exception|failed)\""
echo "  Django логи:       {container_name=~\".*web.*\"}"
echo "  RQ Worker логи:    {container_name=~\".*rqworker.*\"}"
echo ""
echo "✅ Налаштування завершено!"