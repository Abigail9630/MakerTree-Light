#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
streamlit run maker_tree_app.py
