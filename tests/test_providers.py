import httpx
import pytest

from rx_ai_omega.config import Settings
from rx_ai_omega.providers import (
    GenerationRequest,
    MockProvider,
    OllamaProvider,
    OpenAIResponsesProvider,
    ProviderError,
)

REQUEST = GenerationRequest(instructions="Be useful", prompt="Summarize", context={"research": "facts"})


def settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, environment="test", **overrides)  # type: ignore[arg-type]


def test_mock_provider_is_deterministic() -> None:
    assert MockProvider().generate(REQUEST) == MockProvider().generate(REQUEST)
    assert "research" in MockProvider().generate(REQUEST)


def test_openai_responses_adapter_parses_output_text() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"output_text": "done"}))
    client = httpx.Client(transport=transport)
    provider = OpenAIResponsesProvider(settings(openai_api_key="secret"), client)
    assert provider.generate(REQUEST) == "done"


def test_ollama_adapter_parses_response() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"response": "local"}))
    client = httpx.Client(transport=transport)
    assert OllamaProvider(settings(), client).generate(REQUEST) == "local"


def test_provider_errors_do_not_expose_response_body() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(401, text="sensitive"))
    provider = OpenAIResponsesProvider(settings(openai_api_key="secret"), httpx.Client(transport=transport))
    with pytest.raises(ProviderError, match="HTTP 401") as error:
        provider.generate(REQUEST)
    assert "sensitive" not in str(error.value)
