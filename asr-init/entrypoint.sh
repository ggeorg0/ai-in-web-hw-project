#!/bin/bash
set -e

MODELS_DIR=${MODELS_DIR:-/models}
TRITON_SCRIPTS_DIR=/opt/gigaam_repo/triton_scripts
MODEL_TYPE=${MODEL_TYPE:-ctc}
USER_UID=${USER_UID:-1000}
USER_GID=${USER_GID:-1000}

case $MODEL_TYPE in
  ctc)
    ESSENTIAL_DIRS="preprocessing ctc_encoder_trt ctc_postprocessing gigaam_ctc_trt"
    MODEL_PLAN="$MODELS_DIR/ctc_encoder_trt/1/model.plan"
    ;;
  rnnt)
    ESSENTIAL_DIRS="preprocessing gigaam_encoder_trt rnnt_postprocessing gigaam_rnnt_trt"
    MODEL_PLAN="$MODELS_DIR/gigaam_encoder_trt/1/model.plan"
    ;;
  *)
    echo "Error: Unknown MODEL_TYPE=$MODEL_TYPE (expected ctc or rnnt)"
    exit 1
    ;;
esac

echo "=== asr-init: Starting GigaAM model conversion ==="

if [ ! -d "$TRITON_SCRIPTS_DIR" ]; then
    echo "Error: GigaAM repo not mounted at /opt/gigaam_repo"
    exit 1
fi

if [ -f "$MODEL_PLAN" ]; then
    echo "TensorRT engine already exists at $MODEL_PLAN, skipping conversion."
    exit 0
fi

cd "$TRITON_SCRIPTS_DIR"

echo "Converting v3_${MODEL_TYPE} model to ONNX FP16..."
python3 run_convert_onnx.py "v3_${MODEL_TYPE}"

echo "Converting ONNX to TensorRT..."
# Override script defaults on the fly via sed to keep GigaAM submodule unchanged:
#   workspace 3072 MiB instead of 8192
#   opt/max batch = 1 instead of 8/32
sed -e 's/--memPoolSize=workspace:[0-9]*/--memPoolSize=workspace:3072/' \
    -e 's/\(--\(opt\|max\)Shapes=[a-z_]*\):[0-9]*x/\1:1x/g' \
    -e 's/\(,[a-z_]*\):[0-9]\+/\1:1/g' \
    run_convert_trt.sh | bash -s "$MODEL_TYPE"

echo "Copying Triton model repository to $MODELS_DIR..."
mkdir -p "$MODELS_DIR"
for dir in $ESSENTIAL_DIRS; do
    cp -r "repos/$dir" "$MODELS_DIR/"
done

echo "Cleaning up generated artifacts from GigaAM repo..."
find repos \( -name '*.onnx' -o -name '*.onnx.data' -o -name 'config.yaml' -o -name 'model.plan' \) -exec rm -f {} +

echo "Fixing ownership of $MODELS_DIR to $USER_UID:$USER_GID..."
chown -R "$USER_UID:$USER_GID" "$MODELS_DIR"

echo "=== asr-init: Conversion completed successfully ==="