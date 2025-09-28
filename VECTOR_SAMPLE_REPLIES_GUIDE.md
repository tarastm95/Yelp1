# 🔍 Vector-Enhanced Sample Replies Guide

## 📋 Що реалізовано

Система **Sample Replies з векторним пошуком** для **🤖 MODE 2: AI Generated** режиму.

### ✅ Backend компоненти:
- **Vector Models** - `VectorDocument` та `VectorChunk` з pgvector полями
- **Vector PDF Service** - семантичне чанкування з PyMuPDF + OpenAI ембедінги
- **Vector Search Service** - pgvector cosine similarity пошук
- **AI Service інтеграція** - векторний пошук → contextual AI generation
- **API Endpoints** - завантаження, обробка, тестування, діагностика
- **Webhook Logic** - пріоритетна логіка: Vector Search → Legacy → Custom Prompt → Template

### ✅ Frontend компоненти:
- **Vector-Enhanced SampleRepliesManager** - завантаження з векторною візуалізацією
- **Semantic Chunks View** - перегляд створених чанків з типами та метаданими
- **Vector Search Testing** - тестування similarity пошуку
- **Statistics Dashboard** - статистика документів, чанків, токенів

## 🚀 Інструкції для запуску

### 1️⃣ Встановлення залежностей:

```bash
# Install new vector dependencies
cd backend
pip install -r requirements.txt
```

### 2️⃣ Запуск оновленого Docker:

```bash
# Rebuild with pgvector support
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 3️⃣ Застосування міграцій:

```bash
# Create vector tables and enable pgvector
cd backend
python manage.py migrate
```

### 4️⃣ Перевірка pgvector:

```bash
# Connect to database and verify
docker exec -it yelp-database psql -U yelproot -d postgres

# In psql:
\dx  -- Check extensions
SELECT * FROM pg_extension WHERE extname = 'vector';
```

## 📊 Як працює векторне рішення

### 1️⃣ Завантаження PDF:
```
PDF File → PyMuPDF extraction → Semantic chunking → OpenAI embeddings → pgvector storage
```

### 2️⃣ Обробка нового ліда:
```
Customer inquiry → OpenAI embedding → Vector similarity search → Top 5 similar chunks → Contextual AI response
```

### 3️⃣ Пріоритетна логіка:
1. **🔍 Vector Search** - знайти 5 найбільш схожих чанків (similarity > 0.6)
2. **📄 Legacy Fallback** - якщо векторний пошук не працює
3. **🎯 Custom Prompt** - якщо Sample Replies недоступні
4. **📝 Template** - якщо AI взагалі не працює

## 🎯 Використання

### 1️⃣ Налаштування бізнесу:
1. Відкрийте `/settings` → оберіть бізнес
2. Виберіть **🤖 AI GENERATED** режим  
3. Прокрутіть до **"🔍 MODE 2: Vector-Enhanced Sample Replies"**

### 2️⃣ Завантаження Sample Replies:
- **Варіант 1**: Завантажте PDF файл (автоматичне чанкування)
- **Варіант 2**: Вставте текст (ручний ввід з векторизацією)

### 3️⃣ Діагностика:
- **"Test Vector Search"** - перевірити similarity пошук
- **"View Chunks"** - переглянути створені semantic chunks
- **Statistics** - кількість документів, чанків, токенів

## 📈 Переваги векторного рішення:

### 🔍 **Semantic Search:**
- Знаходить **найбільш схожі** приклади для кожного запиту
- **Cosine similarity** з OpenAI text-embedding-3-small (1536D)
- **Intelligent chunking** - розділення на логічні секції

### ⚡ **Performance:**
- Тільки **релевантний контекст** передається AI (замість всього тексту)
- **Швидший пошук** з pgvector індексами  
- **Менше токенів** → дешевші API calls

### 📊 **Analytics:**
- **Chunk types**: `inquiry`, `response`, `example`, `general`
- **Similarity scores** - точність знайдених матчів
- **Token usage** - оптимізація для AI моделей

## 🔧 Технічні деталі

### **Database Schema:**
```sql
-- Vector documents table
CREATE TABLE webhooks_vectordocument (
    id SERIAL PRIMARY KEY,
    business_id VARCHAR(128),
    filename VARCHAR(255),
    file_hash VARCHAR(64) UNIQUE,
    chunk_count INTEGER,
    total_tokens INTEGER,
    processing_status VARCHAR(20),
    embedding_model VARCHAR(50) DEFAULT 'text-embedding-3-small',
    embedding_dimensions INTEGER DEFAULT 1536,
    metadata JSONB
);

-- Vector chunks table with embeddings
CREATE TABLE webhooks_vectorchunk (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES webhooks_vectordocument(id),
    content TEXT,
    chunk_type VARCHAR(20),
    token_count INTEGER,
    embedding vector(1536),  -- pgvector field
    metadata JSONB
);

-- Vector similarity indexes
CREATE INDEX webhooks_vectorchunk_embedding_cosine_idx 
ON webhooks_vectorchunk 
USING ivfflat (embedding vector_cosine_ops);
```

### **API Endpoints:**
- `POST /api/webhooks/sample-replies/upload/` - завантаження файлу
- `POST /api/webhooks/sample-replies/save-text/` - збереження тексту  
- `GET /api/webhooks/sample-replies/status/` - статус для бізнесу
- `POST /api/webhooks/sample-replies/vector-test/` - тестування векторного пошуку
- `GET /api/webhooks/sample-replies/chunks/` - список чанків

### **Fallback Strategy:**
```python
# Priority order in AI generation:
1. Vector Search (if available) → Top 5 similar chunks → Contextual AI
2. Legacy Fallback (if vector fails) → Full text → Standard AI  
3. Custom Prompt (if no Sample Replies) → Business context → AI
4. Template (if AI fails) → Placeholder replacement
```

## ⚠️ Важливі примітки

### **Dependency Requirements:**
- `PyMuPDF>=1.23.0` - PDF parsing
- `pgvector>=0.2.4` - PostgreSQL vector support  
- `tiktoken>=0.5.0` - OpenAI tokenizer
- `numpy>=1.24.0` - Vector operations

### **Docker Requirements:**
- `pgvector/pgvector:pg16` image замість звичайного postgres
- Vector extension initialization script

### **OpenAI API Usage:**
- **text-embedding-3-small** для ембедінгів (1536 dimensions)
- **Batch processing** до 100 текстів одночасно
- **Rate limiting** згідно з AISettings

## 🎉 Результат

Тепер система **автоматично знаходить найбільш схожі приклади** з ваших Sample Replies та генерує **контекстуальні персоналізовані відповіді** у тому ж стилі, використовуючи найсучасніші техніки семантичного пошуку та ембедінгів OpenAI!
