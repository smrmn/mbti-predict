import json
import logging
import requests
import config

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Модели перебираются по порядку при rate limit или ошибке
MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-120b:free",
    "google/gemma-4-31b-it:free",
    "deepseek/deepseek-v4-flash:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]


def get_prediction(mbti_type: str) -> str:
    """Генерирует предсказание через OpenRouter, перебирая модели при ошибках."""

    prompt = (
        f"Дай не глобальное, но содержательное предсказание на сегодня "
        f"не длиннее 100 символов для человека с указанным MBTI-типом личности: {mbti_type}. "
        f"Сделай его жизнеутверждающим, позитивным и подходящим по слогу к указанному "
        f"MBTI-психотипу. Не указывай сам психотип в ответе."
    )

    last_error = None
    for model in MODELS:
        try:
            response = requests.post(
                url=OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "model": model,
                    "max_tokens": 100,
                    "messages": [{"role": "user", "content": prompt}],
                }),
                timeout=30,
            )

            logger.info(f"[{model}] status: {response.status_code}")

            if response.status_code in (429, 503, 502):
                logger.warning(f"[{model}] rate limited, trying next...")
                continue

            if response.status_code == 404:
                logger.warning(f"[{model}] not found, trying next...")
                continue

            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
            logger.info(f"[{model}] success")
            return "🔮 ПСИХОПОЛЕ ГОВОРИТ\n\n" + text

        except Exception as e:
            logger.error(f"[{model}] error: {e}")
            last_error = e
            continue

    raise RuntimeError(f"Все модели недоступны. Последняя ошибка: {last_error}")
