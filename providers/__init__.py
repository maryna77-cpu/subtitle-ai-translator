from .base import BaseProvider, ProviderError, ProviderResult
from .http_json import GenericJSONHTTPProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider
from .openai_compatible import OpenAICompatibleProvider


def build_provider(cfg: dict, provider_name: str) -> BaseProvider:
    if provider_name not in cfg["providers"]:
        raise ValueError(f"Provider '{provider_name}' is not defined in config.json")

    item = dict(cfg["providers"][provider_name])
    item["name"] = provider_name
    kind = item.get("type", "openai_compatible")

    if kind == "openai_compatible":
        return OpenAICompatibleProvider(item)
    if kind == "ollama":
        return OllamaProvider(item)
    if kind == "gemini":
        return GeminiProvider(item)
    if kind == "http_json":
        return GenericJSONHTTPProvider(item)
    raise ValueError(f"Unsupported provider type: {kind}")
