import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.vllm_client import call_vllm_extract, PROMPT, JSON_SCHEMA


async def test_call_vllm_extract_returns_products():
    fake_response = MagicMock()
    fake_response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps({"products": ["помидор", "огурец"]})
            )
        )
    ]

    mock_client = MagicMock()
    mock_client.chat = MagicMock()
    mock_client.chat.completions = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch(
        "app.services.vllm_client.AsyncOpenAI", return_value=mock_client
    ):
        result = await call_vllm_extract("купи помидоры и огурцы")

    assert result == ["помидор", "огурец"]

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "Qwen/Qwen3-0.6B"
    assert call_kwargs["messages"][0] == {"role": "system", "content": PROMPT}
    assert call_kwargs["messages"][1] == {"role": "user", "content": "купи помидоры и огурцы"}
    assert call_kwargs["response_format"] == JSON_SCHEMA
    assert call_kwargs["max_tokens"] == 512
    assert call_kwargs.get("temperature") is None


async def test_call_vllm_extract_empty_products():
    fake_response = MagicMock()
    fake_response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps({"products": []})
            )
        )
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch(
        "app.services.vllm_client.AsyncOpenAI", return_value=mock_client
    ):
        result = await call_vllm_extract("Сегодня хорошая погода")

    assert result == []


async def _check_vllm_available() -> bool:
    try:
        from app.config import VLLM_URL  # noqa: E402
        from openai import AsyncOpenAI  # noqa: E402

        client = AsyncOpenAI(base_url=f"{VLLM_URL}/v1", api_key="not-needed")
        await client.models.list()
        return True
    except Exception:
        return False


async def test_call_vllm_extract_real_inference():
    if not await _check_vllm_available():
        pytest.skip("vLLM server not available")

    result = await call_vllm_extract("Мне нужно купить помидоры, огурцы и хлеб")
    print(f"\n  vLLM extracted products: {result}")
    assert isinstance(result, list)
    assert len(result) > 0, "Expected at least one product extracted"
    assert all(isinstance(p, str) for p in result)