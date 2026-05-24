#!/bin/bash
set -e

MODELS_DIR=${MODELS_DIR:-/models}
TRITON_SCRIPTS_DIR=/opt/gigaam_repo/triton_scripts
MODEL_TYPE=${MODEL_TYPE:-ctc}

echo "=== asr-init: Starting GigaAM model conversion ==="

if [ ! -d "$TRITON_SCRIPTS_DIR" ]; then
    echo "Error: GigaAM repo not mounted at /opt/gigaam_repo"
    exit 1
fi

if [ ! -d "$MODELS_DIR" ]; then
    mkdir -p "$MODELS_DIR"
fi

ESSENTIAL_DIRS="preprocessing ctc_encoder_trt ctc_postprocessing gigaam_ctc_trt"

if [ ! -f "$MODELS_DIR/preprocessing/config.pbtxt" ]; then
    echo "Initializing model repository structure from $TRITON_SCRIPTS_DIR/repos..."
    for dir in $ESSENTIAL_DIRS; do
        cp -r "$TRITON_SCRIPTS_DIR/repos/$dir" "$MODELS_DIR/"
    done
fi

# Scripts reference paths like repos/ctc_encoder_onnx/1; symlink repos -> .
ln -sfn . "$MODELS_DIR/repos"

MODEL_PLAN="$MODELS_DIR/ctc_encoder_trt/1/model.plan"
if [ -f "$MODEL_PLAN" ]; then
    echo "TensorRT engine already exists at $MODEL_PLAN, skipping conversion."
    exit 0
fi

export HOME="/tmp/.asr_home"
mkdir -p "$HOME"

cd "$MODELS_DIR"

echo "Converting v3_${MODEL_TYPE} model to ONNX FP16..."
python "$TRITON_SCRIPTS_DIR/run_convert_onnx.py" "v3_${MODEL_TYPE}"

echo "Converting ONNX to TensorRT..."
bash "$TRITON_SCRIPTS_DIR/run_convert_trt.sh" "$MODEL_TYPE"

echo "Cleaning up intermediate ONNX artifacts..."
rm -rf "$MODELS_DIR/ctc_encoder_onnx"
rm -f "$MODELS_DIR/repos"

echo "=== asr-init: Conversion completed successfully ==="
