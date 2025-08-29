# RESULT Field Fix для скасованих завдань

## 🚨 Проблема

У Tasks Dashboard (`http://46.62.139.177:3000/tasks`) деякі скасовані повідомлення не мали поля RESULT, тобто не було видно **чому** це повідомлення було скасоване.

## 🔍 Корінь проблеми

### Проблема #1: `reason` міг бути `None` або порожнім
```python
# ДО виправлення:
def _cancel_phone_opt_in_tasks(self, lead_id: str, reason: str | None = None):
    # reason міг бути None, що призводило до порожнього RESULT
    CeleryTaskLog.objects.filter(task_id=p.task_id).update(
        status="REVOKED", result=reason  # ← None тут!
    )
```

### Проблема #2: Виклики функцій без reason
```python
# ДО виправлення:
self.handle_phone_opt_in(lid)  # ← Без reason!
self.handle_phone_available(lid)  # ← Без reason!
```

### Проблема #3: TaskRevokeView з порожнім reason
```python
# ДО виправлення:
reason = request.data.get("reason", "")  # ← Порожній рядок!
```

## ✅ Рішення

### 1. Додано default reasons у всі функції скасування

**`_cancel_phone_opt_in_tasks`:**
```python
def _cancel_phone_opt_in_tasks(self, lead_id: str, reason: str | None = None):
    if reason is None:
        reason = "Consumer replied to phone opt-in flow"
    # ... решта коду
```

**`_cancel_pre_phone_tasks`:**
```python
def _cancel_pre_phone_tasks(self, lead_id: str, reason: str | None = None):
    if reason is None:
        reason = "Phone number became available - switching scenarios"
    # ... решта коду
```

**`_cancel_all_tasks`:**
```python
def _cancel_all_tasks(self, lead_id: str, reason: str | None = None):
    if reason is None:
        reason = "All tasks cancelled due to business intervention"
    # ... решта коду
```

### 2. Виправлено TaskRevokeView

**ДО:**
```python
reason = request.data.get("reason", "")  # Порожній рядок
```

**ПІСЛЯ:**
```python
reason = request.data.get("reason", "Task manually revoked from dashboard")
```

### 3. Додано explicit reasons у всі виклики

**ДО:**
```python
self.handle_phone_opt_in(lid)
self.handle_phone_available(lid)
```

**ПІСЛЯ:**
```python
self.handle_phone_opt_in(lid, reason="CONSUMER_PHONE_NUMBER_OPT_IN_EVENT received")
self.handle_phone_available(lid, reason="Phone number found in consumer message")
```

## 🎯 Результат

### Тепер ВСІ скасовані завдання матимуть поле RESULT з описом причини:

| Сценарій | RESULT |
|----------|--------|
| Phone Opt-In відповідь | `"Consumer replied to phone opt-in flow"` |
| Знайдено номер телефону | `"Phone number became available - switching scenarios"` |
| Бізнес втрутився | `"All tasks cancelled due to business intervention"` |
| Скасовано з dashboard | `"Task manually revoked from dashboard"` |
| CONSUMER_PHONE_NUMBER_OPT_IN_EVENT | `"CONSUMER_PHONE_NUMBER_OPT_IN_EVENT received"` |
| Номер в повідомленні | `"Phone number found in consumer message"` |

## 🧪 Тестування

Створено та пройшовено тести, які підтверджують:
- ✅ Всі функції скасування тепер мають default reasons
- ✅ Всі виклики функцій включають explicit reasons
- ✅ TaskRevokeView надає осмислений default reason
- ✅ RESULT поле буде заповнено для всіх майбутніх скасувань

## 📁 Змінені файли

1. **`backend/webhooks/webhook_views.py`**
   - Додано default reasons у функції скасування
   - Виправлено виклики handle_phone_* функцій

2. **`backend/webhooks/task_views.py`**
   - Змінено default reason у TaskRevokeView

## 🎉 Підсумок

**Проблему повністю вирішено!** Тепер у Tasks Dashboard ви бачитимете чітку причину скасування для кожного завдання в полі RESULT.
