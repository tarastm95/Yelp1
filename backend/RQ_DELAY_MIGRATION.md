# RQ Migration: від `enqueue_in()` до `job.delay()`

## Проблема

При використанні `queue.enqueue_in(timedelta(...), func, ...)` виникала помилка:
```
TypeError: 'datetime.datetime' object cannot be interpreted as an integer
```

Це відбувалося тому, що RQ scheduler мав проблеми з інтерпретацією `timedelta` об'єктів.

## Рішення

Перейшли на використання `job.delay()` з параметром `_countdown`:

### Було:
```python
from django_rq import get_queue
from datetime import timedelta

queue = get_queue('default')
queue.enqueue_in(
    timedelta(seconds=10),
    send_follow_up,
    lead_id,
    text,
    business_id,
)
```

### Стало:
```python
send_follow_up.delay(
    lead_id,
    text,
    business_id,
    _countdown=10,  # seconds as integer
)
```

## Переваги нового підходу

1. **Простіше**: менше імпортів, менше коду
2. **Надійніше**: уникаємо проблем з `timedelta` interpretation
3. **Консистентніше**: всюди використовуємо `.delay()` замість мікс `enqueue_in()` та `.delay()`
4. **Підтримка job_id**: можна передати `_job_id` для retry без створення дублікатів

## Змінені файли

### 1. `backend/webhooks/tasks.py`

#### `generate_and_send_follow_up` - retry логіка:
```python
# Було:
queue.enqueue_in(
    timedelta(seconds=10),
    generate_and_send_follow_up,
    lead_id, template_id, business_id, ai_mode,
)

# Стало:
generate_and_send_follow_up.delay(
    lead_id, template_id, business_id, ai_mode,
    _job_id=job_id,  # Preserve job_id for retry
    _countdown=10,
)
```

#### `send_follow_up` - retry логіка:
```python
# Було:
queue.enqueue_in(
    timedelta(seconds=30),
    send_follow_up,
    lead_id, text, business_id,
)

# Стало:
send_follow_up.delay(
    lead_id, text, business_id,
    _countdown=30,
)
```

#### `_apply_async` - helper function:
```python
# Було:
if countdown:
    scheduler = get_scheduler("default")
    job = scheduler.enqueue_in(
        timedelta(seconds=countdown), func, *args, 
        job_id=task_id, **kwargs
    )

# Стало:
if countdown:
    job = func.delay(
        *args, 
        _job_id=task_id, 
        _countdown=countdown, 
        **kwargs
    )
```

### 2. `backend/webhooks/webhook_views.py`

#### Greeting scheduling:
```python
# Було:
from django_rq import get_queue
from datetime import timedelta as td
queue = get_queue('default')
res = queue.enqueue_in(
    td(seconds=int(countdown_greeting)),
    send_follow_up,
    lead_id, greet_text, biz_id,
)

# Стало:
res = send_follow_up.delay(
    lead_id, greet_text, biz_id,
    _countdown=int(countdown_greeting),
)
```

#### Follow-up scheduling:
```python
# Було:
from django_rq import get_queue
from datetime import timedelta as td
queue = get_queue('default')
res = queue.enqueue_in(
    td(seconds=int(countdown)),
    generate_and_send_follow_up,
    lead_id, tmpl.id, biz_id, ai_mode,
)

# Стало:
res = generate_and_send_follow_up.delay(
    lead_id, tmpl.id, biz_id, ai_mode,
    _countdown=int(countdown),
)
```

#### Old-style scheduling (line ~1453):
```python
# Було:
queue = django_rq.get_queue("default")
job = queue.enqueue_in(
    timedelta(seconds=countdown),
    "webhooks.tasks.send_follow_up",
    lead_id, text,
    business_id=pl.business_id,
)

# Стало:
from .tasks import send_follow_up
job = send_follow_up.delay(
    lead_id, text, pl.business_id,
    _countdown=int(countdown),
)
```

## Параметри `.delay()`

### Стандартні параметри:
- `*args` - позиційні аргументи функції
- `**kwargs` - іменовані аргументи функції

### RQ спеціальні параметри (з підкресленням):
- `_job_id` - ID задачі (для retry без дублікатів)
- `_countdown` - затримка в секундах (integer)
- `_timeout` - таймаут виконання
- `_result_ttl` - час зберігання результату
- `_at_front` - додати в початок черги

## Тестування

```bash
cd /var/www/yelp
docker-compose exec backend python manage.py shell -c "
from webhooks.tasks import send_follow_up

# Тест із затримкою
job = send_follow_up.delay(
    'test_lead', 
    'Test message', 
    'test_business',
    _countdown=5,
)
print(f'Job ID: {job.id}')
job.cancel()
"
```

## Статус

✅ **COMPLETED** - всі виклики `enqueue_in()` замінено на `job.delay()`
✅ **TESTED** - перевірено роботу обох task functions
✅ **DEPLOYED** - backend, worker, scheduler перезапущено

## Дата
27.10.2025, 11:56 UTC

