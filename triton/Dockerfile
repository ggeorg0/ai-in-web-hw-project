FROM nvcr.io/nvidia/tritonserver:26.04-py3

RUN apt-get update && apt-get install -y python3-pip python3-packaging && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir "torch==2.10" "torchaudio==2.10" && rm -rf /root/.cache/pip

COPY common/install-asr-deps.sh /install-asr-deps.sh
RUN chmod +x /install-asr-deps.sh && /install-asr-deps.sh