# Testing Guide: New AI Models with Smart Token Allocation

## 🚀 Quick Start

Your system now has **9 AI models** with **automatic smart token allocation**!

---

## 📋 How to Test (Step by Step)

### 1️⃣ Start Watching Logs

Open terminal and run:
```bash
cd /var/www/yelp
docker-compose logs -f backend | grep -E "Smart budget|Auto-calculated|SUCCESS|FAILED"
```

### 2️⃣ Open Frontend

Navigate to:
```
https://your-domain.com
→ Auto Response Settings
→ Select a business
→ Enable "Use AI for greeting generation"
```

### 3️⃣ Test Each Model

**Scroll to "Advanced AI Model Settings"**

Click dropdown and try each model:

#### ✅ Standard Models (should work instantly):
- **gpt-4o** - Click "Generate Preview"
- **gpt-4o-mini** - Click "Generate Preview"
- **gpt-4.1** - Click "Generate Preview" ⭐ NEW
- **gpt-4.1-mini** - Click "Generate Preview" ⭐ NEW
- **gpt-4.1-nano** - Click "Generate Preview" ⭐ NEW

**Expected:** Fast response, ~500 tokens

#### 🧠 Reasoning Models (now work with smart allocation):
- **gpt-5** - Click "Generate Preview"
- **gpt-5-mini** - Click "Generate Preview"
- **gpt-5-nano** - Click "Generate Preview"

**Expected:** Slower response (~10-15 sec), ~2000-2500 tokens, FULL text

---

## 📊 What to Look For in Logs

### For GPT-4o:
```
📊 Prompt tokens: 2,800
📦 Model 'gpt-4o' context window: 128,000 tokens
🆓 Available for response: 125,200 tokens
📝 Standard model: using 500 tokens
🎯 Auto-calculated token budget: 500 (multiplier: 1x)
✅ SUCCESS
```

### For GPT-5:
```
📊 Prompt tokens: 2,800
📦 Model 'gpt-5' context window: 400,000 tokens
🆓 Available for response: 397,200 tokens
🧠 Reasoning model detected
📈 Smart budget: 500 × 5 = 2,500 tokens
   └─ Estimated: ~1,500 reasoning + ~1,000 text
🎯 Auto-calculated token budget: 2,500 (multiplier: 5x)
✅ SUCCESS (no fallback needed!)
```

---

## ✅ Success Criteria

### Each model should:
1. ✅ Show notification: "Model [name] saved successfully!"
2. ✅ Generate preview without errors
3. ✅ Return non-empty response
4. ✅ No fallback to gpt-4o (except if API error)
5. ✅ Logs show correct multiplier

---

## 🎯 Expected Results

| Model | Response Time | Tokens | Success Rate |
|-------|--------------|--------|--------------|
| gpt-4o | ~2 sec | ~500 | 100% |
| gpt-4o-mini | ~1 sec | ~500 | 100% |
| gpt-4.1 | ~2 sec | ~500 | 100% |
| gpt-4.1-mini | ~1 sec | ~500 | 100% |
| gpt-4.1-nano | ~0.5 sec | ~500 | 100% |
| gpt-5 | ~12 sec | ~2,500 | 100% ⭐ |
| gpt-5-mini | ~8 sec | ~2,000 | 100% ⭐ |
| gpt-5-nano | ~5 sec | ~1,500 | 100% ⭐ |

⭐ = Previously failed, now works!

---

## 🧪 Quick Console Test

```bash
# In Docker container
docker-compose exec backend python3 manage.py shell
```

Then paste:
```python
from webhooks.ai_service import OpenAIService

ai = OpenAIService()

# Test GPT-5 with smart allocation
params = ai._get_api_params_for_model(
    'gpt-5',
    [{'role': 'user', 'content': 'Hello'}],
    500,  # User requests 500
    0.7
)

print(f"✅ GPT-5 gets: {params.get('max_completion_tokens')} tokens")
print(f"   Expected: 2500 (500 × 5)")

# Test GPT-4o
params = ai._get_api_params_for_model(
    'gpt-4o',
    [{'role': 'user', 'content': 'Hello'}],
    500,
    0.7
)

print(f"✅ GPT-4o gets: {params.get('max_tokens')} tokens")
print(f"   Expected: 500 (no multiplier)")
```

Expected output:
```
✅ GPT-5 gets: 2500 tokens
   Expected: 2500 (500 × 5)
✅ GPT-4o gets: 500 tokens
   Expected: 500 (no multiplier)
```

---

## 🎨 Frontend Visual Check

### Temperature Section Should Show:

**When GPT-5 selected:**
```
AI Temperature: [Dropdown disabled]
🔒 GPT-5 uses fixed temperature 1.0 (cannot be changed)

ℹ️ GPT-5 models use a fixed temperature of 1.0 for optimal 
   performance with their reasoning router.
```

**When GPT-4o selected:**
```
AI Temperature: [Dropdown enabled]
Creativity level: Balanced

✅ Fully customizable
```

### Model Settings Support:

**GPT-5:**
```
AI Temperature: [🔒 Fixed at 1.0]
Max Message Length: [✅ Fully Supported]

ℹ️ GPT-5 Info: Uses reasoning router for optimal performance.
   Context window: ~400k tokens
```

**GPT-4o:**
```
AI Temperature: [✅ Fully Supported]
Max Message Length: [✅ Fully Supported]
```

---

## 🐛 Troubleshooting

### GPT-5 Still Returns Empty?
**Check logs for:**
```
Smart budget: 500 × 5 = 2,500
```
If shows `500 × 1`, code didn't update - restart backend.

### Model Not Found Error?
**Check:** Is model name spelled correctly in dropdown?
**Fix:** Should match exactly: `gpt-5`, `gpt-4.1`, etc.

### Temperature Not Disabled for GPT-5?
**Check:** Frontend updated?
**Fix:** Hard refresh browser (Ctrl+Shift+R)

---

## 🎉 Success Checklist

- [ ] Logs show smart multipliers (1x, 3x, 4x, 5x)
- [ ] GPT-5 returns full text (not empty)
- [ ] GPT-4.1 models appear in dropdown
- [ ] Temperature disabled for GPT-5
- [ ] Model save notification appears
- [ ] All 9 models generate previews successfully
- [ ] No fallback needed for GPT-5

---

## 📈 Performance Comparison

Test same prompt with different models and compare:

| Metric | GPT-4o | GPT-4.1 | GPT-5 |
|--------|--------|---------|-------|
| Speed | Fast (~2s) | Fast (~2s) | Slower (~12s) |
| Quality | Excellent | Excellent+ | Best |
| Reasoning | Good | Better | Best |
| Cost | Standard | Standard | 3x |
| Use Case | General | Enhanced | Complex RAG |

---

**Ready to test!** 🚀

Start with GPT-4o (baseline), then try GPT-4.1, then GPT-5.
Watch the logs to see smart allocation in action!

