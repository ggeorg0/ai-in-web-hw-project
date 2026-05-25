import wave
from pathlib import Path

import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.triton_client import call_triton_asr


async def test_call_triton_asr_returns_decoded_text():
    audio = np.array([0.1, -0.2, 0.3], dtype=np.float64)

    mock_response = MagicMock()
    mock_response.as_numpy.return_value = np.array([b"hello world"], dtype=object)

    mock_client = MagicMock()
    mock_client.infer = AsyncMock(return_value=mock_response)
    mock_client.close = AsyncMock()

    with patch(
        "app.services.triton_client.grpcclient.InferenceServerClient",
        return_value=mock_client,
    ):
        result = await call_triton_asr(audio)

    assert result == "hello world"

    assert mock_client.infer.call_args.kwargs["model_name"] == "gigaam_ctc_trt"
    inputs = mock_client.infer.call_args.kwargs["inputs"]
    assert len(inputs) == 2

    assert inputs[0].name() == "audio_batch"
    assert inputs[0].datatype() == "FP32"
    assert inputs[0].shape() == [3]

    assert inputs[1].name() == "audio_lengths"
    assert inputs[1].datatype() == "INT64"
    assert inputs[1].shape() == [1]


async def test_call_triton_asr_returns_empty_on_no_texts():
    mock_response = MagicMock()
    mock_response.as_numpy.return_value = np.array([], dtype=object)

    mock_client = MagicMock()
    mock_client.infer = AsyncMock(return_value=mock_response)
    mock_client.close = AsyncMock()

    with patch(
        "app.services.triton_client.grpcclient.InferenceServerClient",
        return_value=mock_client,
    ):
        result = await call_triton_asr(np.array([0.1], dtype=np.float32))

    assert result == ""


async def test_call_triton_asr_creates_client_with_configured_url():
    mock_client_class = MagicMock()
    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.as_numpy.return_value = np.array([b"test"], dtype=object)
    mock_instance.infer = AsyncMock(return_value=mock_response)
    mock_instance.close = AsyncMock()
    mock_client_class.return_value = mock_instance

    with patch(
        "app.services.triton_client.grpcclient.InferenceServerClient",
        mock_client_class,
    ), patch("app.services.triton_client.TRITON_GRPC_URL", "triton-test:8001"):
        await call_triton_asr(np.array([0.1], dtype=np.float32))

    mock_client_class.assert_called_once_with(url="triton-test:8001")


async def _check_triton_available() -> bool:
    try:
        from app.config import TRITON_GRPC_URL  # noqa: E402
        import tritonclient.grpc.aio as grpcclient  # noqa: E402

        client = grpcclient.InferenceServerClient(url=TRITON_GRPC_URL)
        return await client.is_server_live()
    except Exception:
        return False


async def test_call_triton_asr_real_inference():
    if not await _check_triton_available():
        pytest.skip("Triton Inference Server not available")

    wav_path = Path(__file__).parent / "example.wav"
    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.readframes(wf.getnframes())
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

    result = await call_triton_asr(audio)
    print(f"\n  Triton ASR transcription: {result!r}")
    assert isinstance(result, str)
    assert result.strip(), "Expected non-empty transcription from Triton"
