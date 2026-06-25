# MakerTree-Beta

Streamlit app for the **Maker Tree** — a creative workflow for makers:

**Rain → Roots → Trunk → Branches → Bark → Leaves → Soil** (Picnic is a side path for inner work)

**Build with Gemini X Prize** submission. **MakerTree-Beta** ($2.99) — the starting tree; a fuller MakerTree comes later. Not a “lite” afterthought.

## Run locally

```bash
git clone https://github.com/Abigail9630/MakerTree-Light.git
cd MakerTree-Light
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run maker_tree_app.py
```

Or: `./run.sh`

Works in a **phone or laptop browser**.

## Local Talis — Gemma 2B (on the maker's machine)

**Important:** MakerTree-Beta is a Streamlit app (the tree UI). **Gemma is a separate brain** that runs beside it — like having Photoshop and a plugin. Today those are two pieces; a future paid installer can bundle them into one download.

### What you use today (llama.cpp)

You already have llama.cpp — **no Ollama required.**

1. Download a **Gemma 2 2B GGUF** (quantized, ~1–2 GB), e.g. from Hugging Face  
2. Start the server (example):

```bash
llama-server -m /path/to/gemma-2-2b-it-Q4_K_M.gguf --port 8080
```

3. Run MakerTree-Beta → **Picnic** → **Ask Talis**

Optional env: `MAKERTREE_LLM_BACKEND=llama_cpp`, `LLAMA_CPP_HOST=http://127.0.0.1:8086` (any free port)

Example on port **8086** if 8080 is busy:

```bash
llama-server -m /path/to/gemma-2-2b-it-Q4_K_M.gguf --port 8086
export LLAMA_CPP_HOST=http://127.0.0.1:8086
streamlit run maker_tree_app.py
```

### Alternative: Ollama

If a maker prefers one installer: `ollama pull gemma2:2b` — the app detects it automatically.

### What a $2.99 customer gets (honest picture)

| Today (Beta on GitHub) | Future (paid product) |
|------------------------|------------------------|
| App code + UI | Same tree, polished installer |
| **They** install llama.cpp or Ollama + GGUF | **You** ship app + runtime + model in one package |
| Works without AI (text + CSV) | Same — AI optional but bundled |

**Gemma is not inside the Streamlit file.** For checkout at $2.99 you will eventually either:
- **Bundle** llama.cpp + GGUF in your installer (best “just works”), or  
- **Document** a one-time setup (fine for Beta), or  
- **Cloud** Talis (ongoing cost — not the default for this vision)

Without a local server running, **Ask Talis** uses a gentle written fallback — the tree still works.

### Optional: Gemini (cloud)

Only for **Parse with Gemini** on Roots. Free key from Google AI Studio. Not required for Picnic.

## How AI personalization works

1. **Sycamore Grove** — craft type, tools, materials  
2. **Section guardrails** — Talis never bombards after a brain dump  
3. **Gemma 2B (local)** — niche packs per craft on Picnic (fiber vs wood vs clay)  
4. **Gemini (optional)** — one Roots parse if you want cloud polish  

## Example personas (judges / demos)

**Cake decorator** — Picnic stall: over-excited · Trunk: display humidity · Bark: reel storyboard  

**Glass blower** — Picnic: imposter · Trunk: annealing fear · Roots: hand-pulled cane edge  

**Blacksmith** — Picnic: skill gap on tongs · Bark: spark clip · Branches: forge + Etsy  

## What’s in the repo

- `maker_tree_app.py` — main app  
- `talis_gemma.py` — local Gemma 2B via Ollama  
- `assets/` — banners, tree, logo  
- `Rose.md`, `Google Tools/Products.md`  

## Status

- Rain through Soil + Picnic side path  
- Leaves CSV upload  
- Gemma wired on Picnic (**Ask Talis**)  
- Grove form URL: placeholder  

## GitHub

https://github.com/Abigail9630/MakerTree-Light  
*(Repo name may update to MakerTree-Beta; product name is MakerTree-Beta.)*
