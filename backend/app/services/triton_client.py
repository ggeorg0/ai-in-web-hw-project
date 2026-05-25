import numpy as np
import tritonclient.grpc.aio as grpcclient

from ..config import TRITON_GRPC_URL


async def call_triton_asr(audio: np.ndarray) -> str:
    audio_batch = audio.astype(np.float32)
    audio_lengths = np.array([len(audio)], dtype=np.int64)

    client = grpcclient.InferenceServerClient(url=TRITON_GRPC_URL)

    try:
        input_audio = grpcclient.InferInput("audio_batch", audio_batch.shape, "FP32")
        input_audio.set_data_from_numpy(audio_batch)

        input_lengths = grpcclient.InferInput("audio_lengths", audio_lengths.shape, "INT64")
        input_lengths.set_data_from_numpy(audio_lengths)

        response = await client.infer(
            model_name="gigaam_ctc_trt",
            inputs=[input_audio, input_lengths],
        )

        texts_bytes = response.as_numpy("texts")
        texts = [t.decode("utf-8") for t in texts_bytes]
        return texts[0] if texts else ""
    finally:
        await client.close()