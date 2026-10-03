from __future__ import annotations

import json
import os

from openai import OpenAI

from .base import BaseProvider, ProviderError, ProviderResult


class OpenAICompatibleProvider(BaseProvider):
    def __init__(self, cfg: dict):
        self.name = cfg.get("name", "openai_compatible")
        api_key = cfg.get("api_key")
        if not api_key and cfg.get("api_key_env"):
            api_key = os.getenv(cfg["api_key_env"])
        # Some local OpenAI-compatible servers do not require a real key.
        api_key = api_key or "not-needed"

        self.model = cfg["model"]
        self.client = OpenAI(
            api_key=api_key,
            base_url=cfg.get("base_url"),
            timeout=float(cfg.get("timeout_seconds", 180)),
            max_retries=0,
        )
        self.max_tokens_field = cfg.get("max_tokens_field", "max_tokens")
        self.extra_body = cfg.get("extra_body", {})

    def generate(self, system_prompt, user_prompt, *, temperature, max_output_tokens):
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        kwargs[self.max_tokens_field] = max_output_tokens
        if self.extra_body:
            kwargs["extra_body"] = self.extra_body

        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise ProviderError(str(exc), raw=exc) from exc

        choice = response.choices[0]
        content = choice.message.content or ""
        usage = None
        if getattr(response, "usage", None):
            usage = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
                "completion_tokens": getattr(response.usage, "completion_tokens", None),
                "total_tokens": getattr(response.usage, "total_tokens", None),
            }
        return ProviderResult(content=content, raw=response, usage=usage)
