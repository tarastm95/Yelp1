helper_functions = """
    def _prepare_messages_for_model(self, model: str, system_prompt: str, user_prompt: str) -> list:
        \"\"\"Підготовка повідомлень з урахуванням особливостей різних моделей\"\"\"
        
        if model.startswith(\"o1\"):
            # o1 моделі не підтримують system role
            # Комбінуємо system prompt з user prompt
            combined_prompt = f\"{system_prompt}\\n\\nUser request: {user_prompt}\"
            logger.info(f\"[AI-SERVICE] o1 model detected: combining system and user prompts\")
            return [{\"role\": \"user\", \"content\": combined_prompt}]
        else:
            # Стандартні моделі підтримують system role
            return [
                {\"role\": \"system\", \"content\": system_prompt},
                {\"role\": \"user\", \"content\": user_prompt}
            ]

    def _get_api_params_for_model(self, model: str, messages: list, max_tokens: int, temperature: float) -> dict:
        \"\"\"Отримання параметрів API з урахуванням обмежень моделі\"\"\"
        
        params = {
            \"model\": model,
            \"messages\": messages
        }
        
        if model.startswith(\"o1\"):
            # o1 моделі не підтримують temperature та max_tokens
            logger.info(f\"[AI-SERVICE] o1 model: skipping temperature and max_tokens parameters\")
        else:
            # Стандартні моделі підтримують всі параметри
            params[\"max_tokens\"] = max_tokens
            params[\"temperature\"] = temperature
            logger.info(f\"[AI-SERVICE] Standard model: using all parameters\")
        
        return params
"""
print("Helper functions ready for manual insertion")
