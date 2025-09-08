# Debugging Auto-Response Issues

This guide helps you debug why auto-responses are incorrectly identified as manual business responses.

## 🔍 Root Causes Identified

### 1. **Hardcoded `from_backend=False` in Webhooks**
The webhook processing always sets `from_backend=False` initially, even for messages sent by your backend.

### 2. **Timing Race Condition** 
- Your `send_follow_up` task creates `LeadEvent` with `from_backend=True`
- Yelp webhook arrives almost simultaneously
- Webhook overwrites with `from_backend=False`

### 3. **Event ID Mismatch**
- Backend creates custom event IDs: `backend_sent_{uuid}`  
- Yelp webhooks use different event IDs
- System can't match them as the same event

## 🛠️ New Debugging Tools

### 1. Debug Lead Command
Analyze a specific lead with detailed information:

```bash
# Basic analysis
cd /var/www/yelp/backend
python manage.py debug_lead 6KPmcTnNXKnw9QlYO1BNCg

# Show all options
python manage.py debug_lead 6KPmcTnNXKnw9QlYO1BNCg --show-logs --show-events --show-tasks
```

**What it shows:**
- ✅ ProcessedLead information
- 📝 All LeadEvent records with `from_backend` analysis
- ⏰ Pending tasks (active/inactive)
- 🤖 Auto-response detection issues
- 📋 Filtered Docker logs

### 2. Log Filter Script
Filter Docker logs by Lead ID with color coding:

```bash
# Show last 100 entries (default)  
cd /var/www/yelp/backend
python scripts/filter_logs.py 6KPmcTnNXKnw9QlYO1BNCg

# Show last 50 entries
python scripts/filter_logs.py 6KPmcTnNXKnw9QlYO1BNCg 50

# Show all entries for this lead
python scripts/filter_logs.py 6KPmcTnNXKnw9QlYO1BNCg 1000
```

**Color coding:**
- 🔴 **Red**: Errors
- 🟡 **Yellow**: Warnings  
- 🔴 **Bold Red**: Task cancellations
- 🟢 **Green**: Automated messages
- 🟡 **Bold Yellow**: Manual messages

## 📊 Enhanced Webhook Logging

The webhook processing now includes detailed analysis:

```bash
[WEBHOOK] =================== BIZ EVENT ANALYSIS ===================
[WEBHOOK] Event details:
[WEBHOOK] - Event ID: JyfurKEyyZs-2wHC1tZk5w
[WEBHOOK] - User type: BIZ
[WEBHOOK] - Text preview: 'Business, If it makes it easier for you...'
[WEBHOOK] - Full text: 'Business, If it makes it easier for you, we can start with a quick phone consultation — no pressure, just a chance to talk through your goals and see what makes sense. Would that help?'
[WEBHOOK] - Text hash: -1234567890
[WEBHOOK] - defaults.from_backend: False
[WEBHOOK] 🔍 CHECKING FOR EXISTING BACKEND EVENTS:
[WEBHOOK] - Method 1 (text match): Found
[WEBHOOK]   ↳ Existing event ID: backend_sent_abc123
[WEBHOOK]   ↳ Created at: 2025-09-08 06:57:06
[WEBHOOK]   ↳ Task ID in raw: 96e6a268-d7a1-448d-b9c2-40aa5657795f
[WEBHOOK] 🎯 FINAL DECISION:
[WEBHOOK] - is_backend_message: True
[WEBHOOK] 🤖 AUTOMATED BIZ MESSAGE - This is our own follow-up
[WEBHOOK] 🔒 PRESERVING follow-up tasks - not cancelling
```

## 🔧 Detection Logic

The enhanced logic now checks **3 methods**:

1. **Text Match**: Look for existing `LeadEvent` with same text and `from_backend=True`
2. **Recent Backend Events**: Check for any backend events in last 5 minutes  
3. **Matching Tasks**: Look for `LeadPendingTask` with same text

**Decision Logic:**
```python
is_backend_message = (
    existing_backend_event is not None or
    defaults.get("from_backend", False) or  
    recent_tasks.exists()
)
```

## 🚀 Testing the Fix

1. **Trigger a new lead** to test the enhanced detection
2. **Monitor the logs** using the new tools:
   ```bash
   python scripts/filter_logs.py YOUR_LEAD_ID | grep "BIZ EVENT ANALYSIS" -A 20
   ```
3. **Verify** that auto-responses show:
   - `🤖 AUTOMATED BIZ MESSAGE`  
   - `🔒 PRESERVING follow-up tasks`

## ⚠️ Troubleshooting

If auto-responses are still being cancelled:

1. **Check timing**: The LeadEvent with `from_backend=True` must be created before the webhook
2. **Verify text matching**: The text must match exactly between task and webhook
3. **Review logs**: Look for "METHOD 1", "METHOD 2", "METHOD 3" results

## 📝 Log Analysis Tips

Look for these patterns in logs:

**✅ Good (Automated message detected):**
```
[WEBHOOK] - Method 1 (text match): Found
[WEBHOOK] 🤖 AUTOMATED BIZ MESSAGE
[WEBHOOK] 🔒 PRESERVING follow-up tasks
```

**❌ Bad (Incorrectly identified as manual):**
```
[WEBHOOK] - Method 1 (text match): Not found
[WEBHOOK] 👨‍💼 MANUAL BIZ MESSAGE  
[WEBHOOK] 🛑 CANCELLING ALL FOLLOW-UP TASKS
```

Use `python manage.py debug_lead <lead_id>` to get a complete analysis of why detection failed.
