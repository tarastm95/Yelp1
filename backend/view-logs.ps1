#!/usr/bin/env powershell

# Скрипт для перегляду логів Yelp системи
# Використання: .\view-logs.ps1 [сервіс] [опції]

param(
    [string]$Service = "all",
    [int]$Lines = 100,
    [switch]$Follow,
    [switch]$Help
)

if ($Help) {
    Write-Host "🔍 Yelp Logs Viewer" -ForegroundColor Green
    Write-Host ""
    Write-Host "Використання:" -ForegroundColor Yellow
    Write-Host "  .\view-logs.ps1                    # Всі логи (останні 100 рядків)"
    Write-Host "  .\view-logs.ps1 web                # Тільки веб-сервер"
    Write-Host "  .\view-logs.ps1 web -Follow        # Слідкування за логами в реальному часі"
    Write-Host "  .\view-logs.ps1 all -Lines 500     # Останні 500 рядків"
    Write-Host ""
    Write-Host "Доступні сервіси:" -ForegroundColor Yellow
    Write-Host "  web, rqworker, rqscheduler, redis, db, dozzle, all"
    Write-Host ""
    Write-Host "Веб-інтерфейс логів: http://localhost:9999" -ForegroundColor Cyan
    exit 0
}

Write-Host "📋 Yelp Logs Viewer" -ForegroundColor Green
Write-Host "Сервіс: $Service | Рядків: $Lines | Слідкування: $Follow" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

# Перевіряємо чи працює Docker Compose
try {
    $composeStatus = docker-compose ps -q 2>$null
    if (-not $composeStatus) {
        Write-Host "⚠️  Docker Compose не запущений!" -ForegroundColor Red
        Write-Host "Запустіть: docker-compose up -d" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "❌ Помилка підключення до Docker" -ForegroundColor Red
    exit 1
}

# Побудова команди docker-compose logs
$cmd = "docker-compose logs"

if ($Service -ne "all") {
    $cmd += " $Service"
}

$cmd += " --tail $Lines"

if ($Follow) {
    $cmd += " --follow"
}

Write-Host "Виконую: $cmd" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

# Запускаємо команду
Invoke-Expression $cmd 