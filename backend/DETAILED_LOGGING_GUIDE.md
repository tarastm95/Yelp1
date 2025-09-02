# 🔍 Детальне логування Phone Opt-In системи

## 📋 Огляд

Додано **детальне логування** для всіх трьох сценаріїв автовідповідей, щоб точно відстежувати логіку та виявляти проблеми.

## 🎯 Три основні сценарії

### 1. 📱 **Phone Opt-In Scenario** 
- `phone_opt_in=True, phone_available=False`
- Споживач погодився надати номер телефону через Yelp
- **Лог мітки:** `PHONE OPT-IN`, `📱`

### 2. 📞 **Phone Available Scenario**
- `phone_opt_in=False, phone_available=True` 
- Споживач надав номер телефону в тексті повідомлення
- **Лог мітки:** `PHONE AVAILABLE`, `📞`

### 3. 💬 **No Phone Scenario**
- `phone_opt_in=False, phone_available=False`
- Звичайні повідомлення без номера телефону
- **Лог мітки:** `NO PHONE`, `Customer Reply`, `💬`

## 🔍 Ключові лог-повідомлення для відстеження

### При обробці Consumer Events:
```
[WEBHOOK] 🔍 CHECKING FOR PHONE OPT-IN CONSUMER RESPONSE
[WEBHOOK] LeadDetail flags: {'phone_opt_in': True, 'phone_number': '+1234567890'}
[WEBHOOK] 📊 ALL EXISTING ACTIVE TASKS: 3
[WEBHOOK] - Task task_123: phone_opt_in=True, phone_available=False
```

### При виборі сценарію в handle_new_lead:
```
[AUTO-RESPONSE] 🔍 SCENARIO DETERMINATION:
[AUTO-RESPONSE] - LeadDetail exists: True
[AUTO-RESPONSE] - phone_opt_in: True
[AUTO-RESPONSE] 📱 SCENARIO SELECTED: PHONE OPT-IN
[AUTO-RESPONSE] ✅ Phone opt-in scenario tasks created
```

### При обробці Phone Opt-In:
```
[AUTO-RESPONSE] 📱 STARTING handle_phone_opt_in
[AUTO-RESPONSE] 🔍 PHONE OPT-IN SCENARIO ANALYSIS:
[AUTO-RESPONSE] - Trigger reason: CONSUMER_PHONE_NUMBER_OPT_IN_EVENT received
[AUTO-RESPONSE] 📋 EXISTING ACTIVE TASKS BEFORE PROCESSING:
[AUTO-RESPONSE] - Total active tasks: 2
```

### При скасуванні завдань:
```
[AUTO-RESPONSE] 🚫 STARTING _cancel_pre_phone_tasks
[AUTO-RESPONSE] 📊 ALL ACTIVE TASKS BEFORE PRE-PHONE CANCELLATION:
[AUTO-RESPONSE] - Task task_456: phone_opt_in=True, phone_available=False, active=True
[WEBHOOK] 📊 TASKS AFTER CANCELLATION: 0
```

### При створенні завдань:
```
[AUTO-RESPONSE] 🎯 SCENARIO: 📱 PHONE OPT-IN ONLY
[AUTO-RESPONSE] This will look for AutoResponseSettings with:
[AUTO-RESPONSE] - phone_opt_in=True
[AUTO-RESPONSE] - phone_available=False
```

## 🚨 Проблемні ситуації для відстеження

### 1. **Дублювання завдань**
Шукайте:
```
[AUTO-RESPONSE] 📊 ALL EXISTING ACTIVE TASKS: 6  # ← Забагато завдань!
[AUTO-RESPONSE] - Task A: phone_opt_in=True, phone_available=False
[AUTO-RESPONSE] - Task B: phone_opt_in=False, phone_available=False  # ← Конфлікт!
```

### 2. **Невірний сценарій**
Шукайте:
```
[AUTO-RESPONSE] 💬 SCENARIO SELECTED: NO PHONE  # ← Але має бути Phone Opt-in!
[WEBHOOK] LeadDetail flags: {'phone_opt_in': True, 'phone_number': '+1234567890'}
```

### 3. **Завдання не скасовуються**
Шукайте:
```
[WEBHOOK] 📊 TASKS AFTER CANCELLATION: 3  # ← Завдання залишилися!
[AUTO-RESPONSE] Found 0 pending pre-phone tasks to cancel  # ← Нічого не знайдено
```

### 4. **Неправильні AutoResponseSettings**
Шукайте:
```
[AUTO-RESPONSE] 📊 ALL AutoResponseSettings in database:
[AUTO-RESPONSE] - ID=37, phone_opt_in=False, phone_available=False, enabled=True
[AUTO-RESPONSE] - ID=38, phone_opt_in=True, phone_available=False, enabled=False  # ← Вимкнено!
```

## 📊 Типова послідовність логів для Phone Opt-In

### 1. Новий лід з phone opt-in:
```
[AUTO-RESPONSE] 🆕 STARTING handle_new_lead
[AUTO-RESPONSE] 🔍 SCENARIO DETERMINATION:
[AUTO-RESPONSE] - phone_opt_in: True
[AUTO-RESPONSE] 📱 SCENARIO SELECTED: PHONE OPT-IN
[AUTO-RESPONSE] ✅ Phone opt-in scenario tasks created
```

### 2. Consumer response на phone opt-in:
```
[WEBHOOK] 👤 PROCESSING CONSUMER EVENT as TRULY NEW
[WEBHOOK] 🔍 CHECKING FOR PHONE OPT-IN CONSUMER RESPONSE
[WEBHOOK] LeadDetail flags: {'phone_opt_in': True, 'phone_number': '+1234567890'}
[WEBHOOK] 📊 ALL EXISTING ACTIVE TASKS: 2
[WEBHOOK] 📱 ВИЯВЛЕНО ВІДПОВІДЬ СПОЖИВАЧА НА PHONE OPT-IN
[WEBHOOK] 📊 TASKS AFTER CANCELLATION: 0
```

## 🛠️ Налагодження

### Для перевірки конкретного ліда:
```bash
# Запустіть діагностичний скрипт
python debug_phone_optin.py

# Або перевірте в Django shell:
from webhooks.models import LeadDetail, LeadPendingTask
ld = LeadDetail.objects.get(lead_id="YOUR_LEAD_ID")
print(f"phone_opt_in: {ld.phone_opt_in}")

tasks = LeadPendingTask.objects.filter(lead_id="YOUR_LEAD_ID", active=True)
for task in tasks:
    print(f"Task {task.task_id}: phone_opt_in={task.phone_opt_in}, phone_available={task.phone_available}")
```

### Фільтрування логів:
```bash
# Тільки phone opt-in події
docker-compose logs web | grep "PHONE OPT-IN"

# Тільки скасування завдань  
docker-compose logs web | grep "CANCELLATION"

# Тільки вибір сценаріїв
docker-compose logs web | grep "SCENARIO"

# Для конкретного ліда
docker-compose logs web | grep "YOUR_LEAD_ID"
```

## 🎉 Результат

Тепер ви маєте **повну видимість** у:
- ✅ Який сценарій обирається і чому
- ✅ Які завдання існують до обробки
- ✅ Які завдання скасовуються і чому
- ✅ Які завдання створюються
- ✅ Фінальний стан всіх завдань
- ✅ Точну послідовність обробки подій

**Логіка phone opt-in тепер повністю прозора!** 🔍✨
