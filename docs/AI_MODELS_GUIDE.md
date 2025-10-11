# AI Models Configuration Guide

## Available OpenAI Models

This document describes all available AI models that can be configured in the system for automated response generation.

---

## Model Overview

### GPT-4o (Default) ⭐
**Status:** Production Ready  
**Context Window:** ~128k tokens  
**Use Case:** General purpose, best quality

- **Recommended for:** Most business scenarios
- **Strengths:** Best compliance with instructions, high quality responses
- **Best For:** Standard auto-responses, customer support
- **Cost:** Standard pricing

---

### GPT-4o Mini 💰
**Status:** Production Ready  
**Context Window:** ~128k tokens  
**Use Case:** Budget-friendly option

- **Recommended for:** Cost-sensitive deployments
- **Strengths:** Fastest & most cost-effective
- **Limitations:** May occasionally skip complex instructions
- **Best For:** High-volume simple responses, testing
- **Cost:** Lowest cost option

---

### GPT-5 🚀
**Status:** Next Generation (2025)  
**Context Window:** ~400k tokens (4x larger than GPT-4o)  
**Use Case:** Advanced RAG with large documents  
**Temperature:** 🔒 Fixed at 1.0 (not adjustable)

- **Recommended for:** Complex RAG scenarios
- **Strengths:** 
  - Massive context window for processing large document sets
  - Intelligent **reasoning router** (fast vs. deep thinking)
  - Superior reasoning and instruction following
  - Automatic task complexity detection
  - Best for feeding large subsets of documents
- **Best For:** 
  - Businesses with extensive knowledge bases
  - Complex multi-document analysis
  - Detailed product/service catalogs
  - Tasks requiring variable complexity handling
- **Limitations:**
  - Temperature cannot be adjusted (fixed at 1.0)
  - Uses `max_completion_tokens` instead of `max_tokens`
- **Cost:** Premium pricing (~3x GPT-4o)

---

### GPT-5 Mini ⚡
**Status:** Next Generation (2025)  
**Context Window:** ~200k tokens  
**Use Case:** Balanced GPT-5 performance  
**Temperature:** 🔒 Fixed at 1.0 (not adjustable)

- **Recommended for:** Most GPT-5 use cases
- **Strengths:**
  - Faster response times than GPT-5
  - More affordable than full GPT-5
  - Good balance of performance and cost
  - Same reasoning router as GPT-5
- **Best For:**
  - Auto-responses with limited context requirements
  - Speed-critical applications
  - Cost-sensitive GPT-5 deployments
- **Limitations:**
  - Temperature fixed at 1.0
  - Uses `max_completion_tokens`
- **Cost:** Mid-tier pricing (~1.5x GPT-4o)

---

### GPT-5 Nano ⚡⚡
**Status:** Next Generation (2025)  
**Context Window:** ~50k tokens  
**Use Case:** Ultra-fast lightweight responses  
**Temperature:** 🔒 Fixed at 1.0 (not adjustable)

- **Recommended for:** High-volume scenarios
- **Strengths:**
  - Extremely fast response generation
  - Lowest latency among GPT-5 family
  - Very cost-effective
  - Same reasoning router architecture
- **Best For:**
  - Very short responses
  - High-volume auto-responses
  - Simple greeting messages
  - Quick acknowledgments
- **Limitations:**
  - Temperature fixed at 1.0
  - Uses `max_completion_tokens`
- **Cost:** Budget pricing (~0.3x GPT-4o)

---

### GPT-4o Realtime 🎙️
**Status:** Specialized  
**Context Window:** ~128k tokens  
**Use Case:** Real-time streaming responses

- **Recommended for:** Live chat scenarios
- **Strengths:**
  - Ultra-low latency streaming
  - Optimized for real-time interactions
  - Excellent for conversational flows
- **Best For:**
  - Live chat support
  - Voice assistant integrations
  - Real-time customer engagement
  - Instant auto-responses
- **Cost:** Standard pricing with streaming benefits

---

## Configuration Locations

### 1. Business-Specific Settings (Recommended)
**Location:** Frontend UI → Auto Response Settings → Advanced AI Model Settings

Configure per business:
1. Select your business from dropdown
2. Navigate to "Advanced AI Model Settings" section
3. Choose model from "OpenAI Model (optional)" dropdown
4. Select AI Temperature if needed

### 2. Global Settings (Fallback)
**Location:** Django Admin → AI Settings

Configure system-wide default:
1. Access Django Admin at `/admin/`
2. Navigate to "Webhooks" → "AI Settings"
3. Select model from "OpenAI model" dropdown
4. This applies when no business-specific model is set

---

## Model Selection Strategy

### Decision Tree

```
Do you need to process large documents? (>100k tokens)
├─ YES → Use GPT-5 (flagship)
└─ NO ↓

Do you need real-time streaming responses?
├─ YES → Use GPT-4o Realtime
└─ NO ↓

Is speed/cost your top priority?
├─ YES ↓
│   └─ Very high volume?
│       ├─ YES → Use GPT-5 Nano
│       └─ NO → Use GPT-4o Mini
└─ NO ↓

Need advanced reasoning?
├─ YES → Use GPT-5 Mini
└─ NO → Use GPT-4o (default)
```

### By Use Case

| Use Case | Recommended Model | Alternative |
|----------|------------------|-------------|
| Standard auto-responses | GPT-4o | GPT-4o Mini |
| Large document RAG | GPT-5 | GPT-5 Mini |
| High-volume simple replies | GPT-5 Nano | GPT-4o Mini |
| Live chat support | GPT-4o Realtime | GPT-4o |
| Cost optimization | GPT-4o Mini | GPT-5 Nano |
| Complex reasoning | GPT-5 | GPT-5 Mini |
| Fast responses | GPT-5 Nano | GPT-4o Mini |

---

## Cost Considerations

**Estimated Relative Costs (GPT-4o = 1.0x)**

| Model | Relative Cost | Speed |
|-------|--------------|-------|
| GPT-4o | 1.0x | Standard |
| GPT-4o Mini | 0.15x | Very Fast |
| GPT-5 | 3.0x | Standard |
| GPT-5 Mini | 1.5x | Fast |
| GPT-5 Nano | 0.3x | Very Fast |
| GPT-4o Realtime | 1.0x | Ultra Fast |

*Note: Actual pricing may vary. Check OpenAI's pricing page for current rates.*

---

## Temperature Settings

### ⚠️ Important: Temperature Support Varies by Model

**GPT-4o Family (✅ Fully Supported):**
- `gpt-4o`, `gpt-4o-mini`, `gpt-4o-realtime`
- Temperature range: **0.0 - 2.0**
- Adjustable in UI
- Default: 0.7

**GPT-5 Family (🔒 Fixed at 1.0):**
- `gpt-5`, `gpt-5-mini`, `gpt-5-nano`
- Temperature: **Fixed at 1.0**
- **Cannot be adjusted** (API will reject other values)
- Optimized for reasoning router performance
- UI will disable temperature selection for these models

### Temperature Guidelines (for GPT-4o models):

- **0.1-0.3:** Very focused, consistent (formal business)
- **0.5-0.7:** Balanced (recommended for most cases)
- **0.8-1.0:** Creative, varied (use with caution)
- **1.1-2.0:** Very creative, experimental (not recommended)

### Why GPT-5 Has Fixed Temperature?

GPT-5 uses a **reasoning router** that automatically decides when to respond quickly vs. when to "think" longer for complex tasks. This intelligent routing system requires a fixed temperature of 1.0 for optimal performance. The model handles creativity/consistency internally based on task complexity.

---

## Migration Guide

### Upgrading from GPT-4o to GPT-5

1. **Assess Context Needs:**
   - Do you currently truncate documents? → GPT-5 can handle full docs
   - Are responses sometimes incomplete? → GPT-5 provides better reasoning

2. **Test with Sample Business:**
   - Select one business for testing
   - Configure GPT-5 in business settings
   - Monitor response quality and cost

3. **Gradual Rollout:**
   - Start with high-value businesses
   - Monitor performance metrics
   - Expand based on results

### Downgrading to Save Costs

1. **Identify Low-Complexity Businesses:**
   - Simple product/service offerings
   - Short standard responses
   - Low document context needs

2. **Switch to Budget Models:**
   - GPT-4o Mini for standard cases
   - GPT-5 Nano for very simple responses

3. **Monitor Quality:**
   - Check if responses still meet quality standards
   - Adjust temperature if needed
   - Switch back if quality drops

---

## Technical Implementation

### Backend Support
- Models stored in `AutoResponseSettings.ai_model` (per business)
- Global fallback in `AISettings.openai_model`
- No validation constraints - any model name accepted
- Max length: 50 characters

### Frontend Integration
- Dropdown in `/frontend/src/AutoResponseSettings.tsx`
- Visual labels and descriptions for each model
- Auto-saves on selection change

### API Integration
- All models use standard OpenAI API
- Realtime model requires streaming API setup
- Context windows automatically handled by API

---

## Troubleshooting

### Model Not Available Error
**Symptom:** API returns model not found  
**Solution:** 
- Verify OpenAI API key has access to selected model
- Check if model is in beta/early access
- Ensure model name is spelled correctly

### Unexpected Costs
**Symptom:** Higher than expected API bills  
**Solution:**
- Review which businesses use premium models (GPT-5)
- Check context window usage in logs
- Consider downgrading low-complexity businesses
- Implement usage monitoring alerts

### Poor Response Quality
**Symptom:** Responses don't follow instructions  
**Solution:**
- Upgrade from Mini/Nano to standard model
- Adjust temperature (lower = more focused)
- Review custom instructions clarity
- Ensure sample replies are comprehensive

### Slow Response Times
**Symptom:** Responses take too long  
**Solution:**
- Switch to faster model (Mini/Nano variants)
- Consider GPT-4o Realtime for live scenarios
- Reduce context size if possible
- Check API rate limits

---

## Future Model Additions

To add new models in the future:

1. **Frontend:** Update dropdown in `AutoResponseSettings.tsx` (lines ~2016-2057)
2. **Backend Admin:** Update `MODEL_CHOICES` in `admin.py` (lines ~14-21)
3. **Documentation:** Update this guide with new model specifications

No database migrations required - CharField accepts any value.

---

## Support

For questions or issues:
- Check OpenAI documentation: https://platform.openai.com/docs
- Review system logs for API errors
- Contact support if model behavior seems incorrect

---

**Last Updated:** 2025-10-11  
**Compatible With:** OpenAI API v1+

