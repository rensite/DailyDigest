"""
Единый интерфейс к LLM с поддержкой 4 провайдеров:
OpenAI, Anthropic, Grok (xAI), Gemini.

Провайдер выбирается через .env (LLM_PROVIDER). Все вызовы идут через
HTTP API напрямую (только requests) — без тяжёлых SDK.

Если ключ не задан или запрос упал — функции возвращают None,
и сервис плавно деградирует к обычной (не-LLM) сводке.
"""
import json
import logging
import requests

log = logging.getLogger("digest.llm")

# Дефолтные модели для каждого провайдера (можно переопределить в .env)
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "grok": "grok-2-latest",
    "gemini": "gemini-1.5-flash",
}


class LLMClient:
    def __init__(self, provider: str, api_key: str, model: str = "",
                 timeout: int = 40):
        self.provider = (provider or "").lower().strip()
        self.api_key = (api_key or "").strip()
        self.model = (model or "").strip() or DEFAULT_MODELS.get(self.provider, "")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.provider and self.api_key)

    def complete(self, system: str, user: str, max_tokens: int = 700,
                 temperature: float = 0.5):
        """Возвращает текст ответа модели или None при любой ошибке."""
        if not self.enabled:
            return None
        try:
            if self.provider == "openai":
                return self._openai(system, user, max_tokens, temperature)
            if self.provider == "anthropic":
                return self._anthropic(system, user, max_tokens, temperature)
            if self.provider == "grok":
                return self._grok(system, user, max_tokens, temperature)
            if self.provider == "gemini":
                return self._gemini(system, user, max_tokens, temperature)
            log.warning("Неизвестный LLM-провайдер: %s", self.provider)
            return None
        except Exception as e:
            log.warning("LLM (%s) ошибка: %s", self.provider, e)
            return None

    def complete_json(self, system: str, user: str, max_tokens: int = 900,
                      temperature: float = 0.3):
        """Как complete, но пытается распарсить ответ как JSON."""
        raw = self.complete(
            system + "\n\nОтвечай ТОЛЬКО валидным JSON, без markdown-обёртки.",
            user, max_tokens, temperature,
        )
        if not raw:
            return None
        return _extract_json(raw)

    # --- провайдеры (OpenAI-совместимый chat/completions) ---

    def _chat_completions(self, base_url, system, user, max_tokens, temperature,
                          extra_headers=None):
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        r = requests.post(base_url, headers=headers,
                          json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

    def _openai(self, system, user, max_tokens, temperature):
        return self._chat_completions(
            "https://api.openai.com/v1/chat/completions",
            system, user, max_tokens, temperature)

    def _grok(self, system, user, max_tokens, temperature):
        # xAI Grok — OpenAI-совместимый endpoint
        return self._chat_completions(
            "https://api.x.ai/v1/chat/completions",
            system, user, max_tokens, temperature)

    def _anthropic(self, system, user, max_tokens, temperature):
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        r = requests.post("https://api.anthropic.com/v1/messages",
                          headers=headers, json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["content"][0]["text"].strip()

    def _gemini(self, system, user, max_tokens, temperature):
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.model}:generateContent?key={self.api_key}")
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        r = requests.post(url, json=payload, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _extract_json(text: str):
    """Достаёт JSON из ответа модели, даже если он в ```json блоке."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
    # Находим первую { и последнюю }
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1:
        start = t.find("[")
        end = t.rfind("]")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(t[start:end + 1])
    except json.JSONDecodeError:
        return None
