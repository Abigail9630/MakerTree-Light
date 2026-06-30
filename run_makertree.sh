#!/bin/bash
# MakerTree-Beta + local Talis URL (llama.cpp on port 8086 by default)
set -e
cd "$(dirname "$0")"
export LLAMA_CPP_HOST="${LLAMA_CPP_HOST:-http://127.0.0.1:8086}"
export MAKERTREE_LLM_BACKEND="${MAKERTREE_LLM_BACKEND:-llama_cpp}"
source .venv/bin/activate
echo "MakerTree-Beta → LLAMA_CPP_HOST=$LLAMA_CPP_HOST"
echo "Start Talis first in another terminal: ./start_talis_server.sh"
exec streamlit run maker_tree_app.py
