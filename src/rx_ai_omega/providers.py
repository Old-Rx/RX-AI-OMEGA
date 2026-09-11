import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from .config import Settings


@dataclass(frozen=True)
class GenerationRequest:
    instructions: str
    prompt: str
    context: dict[str, str]


class ProviderError(RuntimeError):
    pass


class Provider(ABC):
    @abstractmethod
    def generate(self, request: GenerationRequest) -> str: ...


class MockProvider(Provider):
    """Deterministic provider for local development and automated tests."""

    def generate(self, request: GenerationRequest) -> str:
        context_keys = ", ".join(sorted(request.context)) or "none"
        return f"[mock] {request.prompt.strip()} | dependencies: {context_keys}"


class OpenAIResponsesProvider(Provider):
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.Client(timeout=60)

    def generate(self, request: GenerationRequest) -> str:
        assert self.settings.openai_api_key is not None
        response = self.client.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
            json={
                "model": self.settings.openai_model,
                "instructions": request.instructions,
                "input": request.prompt + "\n\nDependency context:\n" + json.dumps(request.context),
            },
        )
        if response.is_error:
            raise ProviderError(f"OpenAI request failed with HTTP {response.status_code}")
        data = response.json()
        output_text = data.get("output_text")
        if isinstance(output_text, str):
            return output_text
        texts = [
            item.get("text", "")
            for output in data.get("output", [])
            for item in output.get("content", [])
            if item.get("type") == "output_text"
        ]
        if not texts:
            raise ProviderError("OpenAI response did not contain output text")
        return "\n".join(texts)


class OllamaProvider(Provider):
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.Client(timeout=120)

    def generate(self, request: GenerationRequest) -> str:
        response = self.client.post(
            f"{self.settings.ollama_base_url.rstrip('/')}/api/generate",
            json={
                "model": self.settings.ollama_model,
                "system": request.instructions,
                "prompt": request.prompt + "\n\n" + json.dumps(request.context),
                "stream": False,
            },
        )
        if response.is_error:
            raise ProviderError(f"Ollama request failed with HTTP {response.status_code}")
        text = response.json().get("response")
        if not isinstance(text, str):
            raise ProviderError("Ollama response did not contain text")
        return text


def build_provider(name: str, settings: Settings, client: httpx.Client | None = None) -> Provider:
    if name == "mock":
        return MockProvider()
    if name == "openai":
        return OpenAIResponsesProvider(settings, client)
    if name == "ollama":
        return OllamaProvider(settings, client)
    raise ProviderError(f"Unsupported provider: {name}")
