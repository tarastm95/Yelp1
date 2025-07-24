#!/bin/bash

# Скрипт для перегляду логів Yelp системи
# Використання: ./view-logs.sh [сервіс] [опції]

SERVICE="${1:-all}"
LINES="${2:-100}"
FOLLOW=""

# Парсинг аргументів
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW="--follow"
            shift
            ;;
        -l|--lines)
            LINES="$2"
            shift 2
            ;;
        -h|--help)
            echo "🔍 Yelp Logs Viewer"
            echo ""
            echo "Використання:"
            echo "  ./view-logs.sh                     # Всі логи (останні 100 рядків)"
            echo "  ./view-logs.sh web                 # Тільки веб-сервер"
            echo "  ./view-logs.sh web --follow        # Слідкування за логами в реальному часі"
            echo "  ./view-logs.sh all --lines 500     # Останні 500 рядків"
            echo ""
            echo "Доступні сервіси:"
            echo "  web, rqworker, rqscheduler, redis, db, dozzle, all"
            echo ""
            echo "Веб-інтерфейс логів: http://localhost:9999"
            exit 0
            ;;
        *)
            if [[ -z "$SERVICE_SET" ]]; then
                SERVICE="$1"
                SERVICE_SET=true
            fi
            shift
            ;;
    esac
done

echo "📋 Yelp Logs Viewer"
echo "Сервіс: $SERVICE | Рядків: $LINES | Слідкування: $([[ -n "$FOLLOW" ]] && echo "Так" || echo "Ні")"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Перевіряємо чи працює Docker Compose
if ! docker-compose ps -q >/dev/null 2>&1; then
    echo "⚠️  Docker Compose не запущений!"
    echo "Запустіть: docker-compose up -d"
    exit 1
fi

# Побудова команди docker-compose logs
CMD="docker-compose logs"

if [[ "$SERVICE" != "all" ]]; then
    CMD="$CMD $SERVICE"
fi

CMD="$CMD --tail $LINES $FOLLOW"

echo "Виконую: $CMD"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Запускаємо команду
exec $CMD 