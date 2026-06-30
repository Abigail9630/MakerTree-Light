#!/bin/bash
# Start local Talis (Gemma 2B) for MakerTree-Beta — keep this terminal open.
set -e
MODEL="${MAKERTREE_GEMMA_GGUF:-$HOME/models/gemma-2-2b-it-Q5_K_S.gguf}"
PORT="${MAKERTREE_LLAMA_PORT:-8086}"
BIN_DIR="$HOME/llama.cpp/build-gemma/bin"

if [[ ! -f "$MODEL" ]]; then
  echo "Model not found: $MODEL"
  echo "Set MAKERTREE_GEMMA_GGUF to your .gguf path."
  exit 1
fi
if [[ ! -x "$BIN_DIR/llama-server" ]]; then
  echo "llama-server not found: $BIN_DIR/llama-server"
  exit 1
fi

echo "Starting Gemma on http://127.0.0.1:$PORT"
echo "Model: $MODEL"
cd "$BIN_DIR"
exec ./llama-server -m "$MODEL" --port "$PORT" -c 4096 --host 127.0.0.1
