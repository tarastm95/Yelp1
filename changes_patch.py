# PATCH FILE FOR SMS FIX - Step by step changes

# CHANGE 1: Function signature
# FROM:
#     def _process_auto_response(
#         self, lead_id: str, phone_opt_in: bool, phone_available: bool
#     ):
# TO:
#     def _process_auto_response(
#         self, lead_id: str, phone_opt_in: bool, phone_available: bool, is_new_lead: bool = False
#     ):

# CHANGE 2: Add logging
# AFTER line 1391, ADD:
#     logger.info(f"[AUTO-RESPONSE] - is_new_lead: {is_new_lead}")

# CHANGE 3: Update reason logic 
# FROM lines 1394-1399:
#     if phone_opt_in:
#         reason = "Phone Opt-in"
#     elif phone_available:
#         reason = "Phone Number Found"
#     else:
#         reason = "Customer Reply"
# TO:
#     if phone_opt_in:
#         reason = "Phone Opt-in"
#     elif phone_available:
#         reason = "Phone Number Found"
#     elif is_new_lead:
#         reason = "New Lead"
#     else:
#         reason = "Customer Reply"

# CHANGE 4: Update handle_new_lead call
# FROM line 929:
#     self._process_auto_response(lead_id, phone_opt_in=False, phone_available=False)
# TO:
#     self._process_auto_response(lead_id, phone_opt_in=False, phone_available=False, is_new_lead=True)

# CHANGE 5: Add SMS skip logic for new leads
# BEFORE line 1556, ADD:
#     # Disable SMS for new leads regardless of AutoResponseSettings
#     if is_new_lead:
#         logger.info(f"[AUTO-RESPONSE] 🚫 SMS DISABLED for New Lead scenario")
#         logger.info(f"[AUTO-RESPONSE] - New leads should not trigger SMS notifications")
#         final_sms_decision = False
#     else:
#         final_sms_decision = should_send_sms and auto_settings.enabled
# AND REPLACE the existing line:
#     final_sms_decision = should_send_sms and auto_settings.enabled
