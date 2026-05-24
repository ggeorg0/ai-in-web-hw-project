#!/bin/bash
set -e

python3 -m pip install --no-cache-dir \
    hydra-core==1.3.* \
    soundfile==0.13.* \
    omegaconf==2.3.* \
    sentencepiece \
    onnx \
    onnxruntime-gpu \
    tqdm
