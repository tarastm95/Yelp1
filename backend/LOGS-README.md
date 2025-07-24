# 📋 Система логування Yelp

## 🎯 Огляд

Ваша система налаштована для **збереження логів протягом місяця** з автоматичною ротацією та стисненням.

## 🔧 Налаштування

### 📁 Зберігання логів
- **Docker логи**: автоматично зберігаються та ротуються
- **Файли логів**: `./logs/` директорія
- **Період зберігання**: 31 день (31 файл по ~100MB кожен)
- **Стиснення**: автоматичне для економії місця

### 📊 Конфігурація по сервісах
- **web, rqworker**: 100MB x 31 файлів
- **redis, db, rqscheduler**: 50MB x 31 файлів  
- **dashboards**: 30-50MB x 31 файлів

## 🖥️ Способи перегляду логів

### 1. 🌐 Веб-інтерфейс (Рекомендовано)
```bash
# Відкрийте у браузері:
http://localhost:9999
```

**Функції Dozzle:**
- 🔍 Реальний час
- 🎯 Фільтрація по сервісах
- 🔎 Пошук по тексту
- 📱 Зручний мобільний інтерфейс
- 📈 Статистика використання

### 2. 🖥️ Командний рядок (PowerShell)
```powershell
# Всі логи (останні 100 рядків)
.\view-logs.ps1

# Конкретний сервіс
.\view-logs.ps1 web
.\view-logs.ps1 rqworker

# Реальний час
.\view-logs.ps1 web -Follow

# Більше рядків
.\view-logs.ps1 all -Lines 500

# Допомога
.\view-logs.ps1 -Help
```

### 3. 🐧 Командний рядок (Linux/Mac)
```bash
# Зробити виконуваним
chmod +x view-logs.sh

# Всі логи
./view-logs.sh

# Конкретний сервіс
./view-logs.sh web

# Реальний час
./view-logs.sh web --follow

# Більше рядків
./view-logs.sh all --lines 500

# Допомога
./view-logs.sh --help
```

### 4. 🐳 Прямі Docker команди
```bash
# Всі сервіси
docker-compose logs --tail 100

# Конкретний сервіс
docker-compose logs web --tail 100

# Реальний час
docker-compose logs web --follow

# З позначками часу
docker-compose logs --timestamps web

# За останню годину
docker-compose logs --since 1h web
```

## 🔍 Фільтрація логів

### Пошук по ключовим словам
```bash
# Пошук помилок
docker-compose logs web | grep -i error

# Пошук по lead ID
docker-compose logs web | grep "lead_id=ABC123"

# Пошук SMS логів
docker-compose logs web | grep "\[SMS-"

# Пошук автовідповідей
docker-compose logs web | grep "\[AUTO-RESPONSE\]"

# Пошук веб-хуків
docker-compose logs web | grep "\[WEBHOOK\]"
```

### PowerShell фільтрація
```powershell
# Пошук помилок
docker-compose logs web | Select-String -Pattern "error" -CaseSensitive:$false

# Пошук по lead ID
docker-compose logs web | Select-String -Pattern "lead_id=ABC123"
```

## 📈 Моніторинг продуктивності

### Розмір логів
```bash
# Linux/Mac
du -sh logs/
docker system df

# Windows
dir logs /s /-c
```

### Статистика логів
```bash
# Кількість рядків за сьогодні
docker-compose logs --since today web | wc -l

# Найактивніші сервіси
docker-compose logs --since 1h | head -1000
```

## 🚨 Типи логів для моніторингу

### 1. 📱 Auto-Response логи
```
[AUTO-RESPONSE] 🆕 STARTING handle_new_lead
[AUTO-RESPONSE] ✅ handle_new_lead completed successfully
```

### 2. 📨 SMS Notification логи
```
[SMS-NOTIFICATION] 📱 SIGNAL TRIGGERED: notify_new_lead
[TWILIO] ✅ SMS sent successfully!
```

### 3. 🌐 Webhook логи
```
[WEBHOOK] 🔍 TRIGGERING NEW LEAD VERIFICATION
[WEBHOOK] ✅ CONVERTING EVENT TO NEW_LEAD
```

### 4. 🔄 Task логи
```
[FOLLOW-UP] 🚀 STARTING send_follow_up task
[FOLLOW-UP] ✅ Message sent successfully!
```

## 🔧 Обслуговування

### Очищення старих логів
```bash
# Видалити логи старші 30 днів (автоматично)
# Docker автоматично управляє ротацією

# Ручне очищення (якщо потрібно)
docker system prune -f
```

### Збільшення періоду зберігання
У `docker-compose.yml` змініть:
```yaml
logging:
  options:
    max-file: "62"  # 2 місяці замість 1
```

### Зменшення розміру файлів
```yaml
logging:
  options:
    max-size: "50m"  # Замість 100m
```

## 🆘 Troubleshooting

### Проблема: Логи не зберігаються
```bash
# 1. Перевірити права доступу
ls -la logs/

# 2. Перезапустити Docker
docker-compose down
docker-compose up -d

# 3. Перевірити налаштування
docker-compose config
```

### Проблема: Dozzle не працює
```bash
# Перевірити статус
docker-compose ps dozzle

# Переглянути логи Dozzle
docker-compose logs dozzle

# Перезапустити
docker-compose restart dozzle
```

### Проблема: Занадто багато логів
```bash
# Тимчасово зменшити логування
docker-compose logs --tail 50

# Змінити рівень логування у коді
# logger.setLevel(logging.WARNING)
```

## 🎯 Корисні команди

```bash
# Швидкий огляд всіх сервісів
docker-compose ps

# Статистика ресурсів
docker stats

# Перезапуск з новими налаштуваннями
docker-compose down && docker-compose up -d

# Backup логів
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/

# Моніторинг у реальному часі
watch 'docker-compose ps && echo "=== Latest logs ===" && docker-compose logs --tail 5'
```

---

## 📞 Контакти

При проблемах з логуванням:
1. Перевірте `docker-compose ps`
2. Подивіться на http://localhost:9999
3. Використайте `.\view-logs.ps1 -Help` 