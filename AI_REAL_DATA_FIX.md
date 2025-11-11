# 🔧 Виправлення використання реальних даних в AI відповідях

## 📋 Опис проблеми

AI генерував відповіді з **плейсхолдерами** замість реальних даних бізнесу:

```
Good morning, Goui! Priority Remodeling specializes in home remodeling 
and we'd be delighted to assist with your project in the 33125 area...
Please give us a call at [phone number] to discuss your project details...
Best regards, [Your Name] Priority Remodeling
```

### ❌ Що було не так:

- AI писав `[phone number]` замість `(305) 816-1560`
- AI писав `[Your Name]` замість `Ben` або `Priority Remodeling Team`
- AI писав `[Location]` замість реальної адреси

## 🔍 Причина проблеми

User prompt не містив **явних інструкцій** про використання реальних даних. Промпт був таким:

```python
Business Information:
Phone: (305) 816-1560
Rating: 4.0/5 stars (12 reviews)

IMPORTANT: Start your response with the time-appropriate greeting...
Customer inquiry requires response based on the information above.
```

AI **бачив** дані, але не мав **явної інструкції** їх використовувати. Натомість, якщо в Custom Instructions були приклади з плейсхолдерами, AI їх копіював.

## ✅ Рішення

### Додано CRITICAL TECHNICAL REQUIREMENTS в user prompt

**Файл:** `/var/www/yelp/backend/webhooks/ai_service.py`  
**Рядки:** 996-1017

### До виправлення:

```python
contextual_prompt = f"""Customer message:
"{customer_text}"

Customer name: {customer_name}
Business name: {business_name}
Time-appropriate greeting: {time_greeting}

Business Information:
{business_info}{vector_context}{length_instruction}

IMPORTANT: Start your response with the time-appropriate greeting ({time_greeting}) followed by the customer's name.

Customer inquiry requires response based on the information above."""
```

### Після виправлення:

```python
contextual_prompt = f"""Customer message:
"{customer_text}"

Customer name: {customer_name}
Business name: {business_name}
Time-appropriate greeting: {time_greeting}

Business Information:
{business_info}{vector_context}{length_instruction}

CRITICAL TECHNICAL REQUIREMENTS:
1. Use REAL business data from the Business Information section above
2. When mentioning contact information, use the ACTUAL phone number provided (not placeholders like [phone number] or [phone])
3. When signing the message, use a real person's name or "{business_name} Team" (not placeholders like [Your Name])
4. All data in Business Information is real and should be used as-is in your response

FORMATTING REQUIREMENTS:
- Start your response with the time-appropriate greeting ({time_greeting}) followed by the customer's name
- Generate a response following your role and communication style guidelines
- Include specific business information when relevant to the customer's inquiry

Generate your response now based on the customer inquiry and your instructions."""
```

## 🎯 Як працює виправлення

### Структура промптів OpenAI:

```python
messages = [
    {"role": "system", "content": custom_instructions},  # Custom Instructions (стиль, особистість)
    {"role": "user", "content": contextual_prompt}       # Завдання + дані + технічні вимоги
]
```

### Пріоритети AI:

1. **SYSTEM (Custom Instructions)** = "ХТО я, ЯК я спілкуюся"
   - Особистість (Ben, We The People Construction)
   - Стиль комунікації (warm, friendly, hook-style questions)
   - Правила (no em dashes, natural language)

2. **USER (contextual prompt)** = "ЩО робити, ТЕХНІЧНІ вимоги"
   - Customer message
   - Business data (phone, rating, location)
   - **CRITICAL TECHNICAL REQUIREMENTS** ← нове!
   - Formatting requirements

### Взаємодія:

```
SYSTEM: "Ти - Ben. Говори тепло, дружньо, природно..."

USER: "Ось запит клієнта про remodeling.
       Ось дані: Phone: (305) 816-1560
       
       CRITICAL: Використовуй РЕАЛЬНИЙ номер телефону,
                НЕ пиши [phone number]!
       
       Відповідай згідно з інструкціями вище."
```

**Результат:** AI дотримується Custom Instructions (стиль Ben) + використовує реальні дані (технічні вимоги).

## 📊 Результат

### До виправлення ❌

```
Good morning, Goui! Priority Remodeling specializes in home remodeling...
Please give us a call at [phone number] to discuss your project details...
Best regards, [Your Name] Priority Remodeling
```

### Після виправлення ✅

```
Good morning, Goui! How's your day going so far?

Thanks for reaching out about your bedroom remodel – sounds like 
you're ready to transform the space and get it done quickly.

Do you already have a vision for what you'd like, or would it 
help to walk through it together? Once we see the space in person, 
we'll be able to map out the next steps.

Feel free to give us a call at (305) 816-1560 if you'd like to chat, 
or just let me know here what day works for a quick visit.

– Ben
Priority Remodeling
```

## ✅ Переваги рішення

### 1. Не конфліктує з Custom Instructions
- ✅ Custom Instructions контролює **стиль і особистість**
- ✅ CRITICAL REQUIREMENTS контролює **технічні аспекти**
- ✅ Вони **доповнюють** одне одного, не конфліктують

### 2. Працює для всіх бізнесів
- ✅ Не потребує оновлення існуючих Custom Instructions
- ✅ Працює автоматично для нових і старих бізнесів
- ✅ Є системним захистом від плейсхолдерів

### 3. Працює для обох режимів
- ✅ **No Phone and Phone Opt-In** режим
- ✅ **Phone Number in Message** режим
- ✅ Обидва використовують той самий код

### 4. Явні інструкції
- ✅ Чітко вказує: "use ACTUAL phone number"
- ✅ Дає приклади заборонених плейсхолдерів
- ✅ Пропонує варіанти підпису

## 🔍 Технічні деталі

### Де застосовується:

1. **AI Full mode** (без Sample Replies)
   - `ai_service.py`, функція `_create_greeting_prompt`
   - Використовується для генерації greeting та follow-up повідомлень

2. **AI Vector mode** (з Sample Replies)
   - Той самий промпт використовується як основа
   - Vector context додається в секцію Business Information

### Які дані передаються:

```python
Business Information:
Phone: (305) 816-1560                      # ✅ Реальний номер
Rating: 4.0/5 stars (12 reviews)          # ✅ Реальний рейтинг
Specializes in: General Contractors        # ✅ Реальні категорії
Address: Miami, FL 33126                   # ✅ Реальна адреса
```

### Як AI їх використовує:

```python
CRITICAL TECHNICAL REQUIREMENTS:
1. Use REAL business data from the Business Information section above
   ↓
   AI: "Ok, я бачу Phone: (305) 816-1560 - це РЕАЛЬНИЙ номер"

2. When mentioning contact information, use the ACTUAL phone number...
   ↓
   AI: "Треба написати (305) 816-1560, а НЕ [phone number]"

3. When signing the message, use a real person's name...
   ↓
   AI: "Підпишусь 'Ben' або 'Priority Remodeling Team', НЕ [Your Name]"
```

## 🎯 Висновок

**Проблема:** AI копіював плейсхолдери з прикладів або генерував власні, не використовуючи реальні дані.

**Причина:** User prompt не містив явних інструкцій про використання реальних даних.

**Рішення:** Додано секцію CRITICAL TECHNICAL REQUIREMENTS з явними інструкціями:
- Використовувати реальні дані з Business Information
- Не використовувати плейсхолдери
- Приклади заборонених плейсхолдерів
- Варіанти правильного підпису

**Результат:** AI тепер **завжди** використовує реальні дані (телефон, ім'я, адресу) замість плейсхолдерів, при цьому дотримуючись стилю та правил з Custom Instructions.

---

**Дата виправлення:** 31 жовтня 2025  
**Файли змінені:** `/var/www/yelp/backend/webhooks/ai_service.py` (рядки 996-1017)  
**Тип виправлення:** Додано технічні інструкції в user prompt без зміни Custom Instructions

