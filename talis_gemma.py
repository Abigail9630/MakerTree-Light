"""
Local Talis voice via Gemma 2B (quantized).

Supports two runtimes (same idea — model runs on the maker's machine, no API key):

1. **llama.cpp server** (recommended if you already use llama.cpp)
   Start: llama-server -m /path/to/gemma-2-2b-it-Q4_K_M.gguf --port 8080

2. **Ollama** (alternative one-click installer)
   ollama pull gemma2:2b

Env:
  MAKERTREE_LLM_BACKEND=auto | llama_cpp | ollama   (default: auto — tries llama.cpp first)
  LLAMA_CPP_HOST=http://127.0.0.1:8080
  OLLAMA_HOST=http://127.0.0.1:11434
  MAKERTREE_GEMMA_MODEL=gemma2:2b   (Ollama only)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

DEFAULT_GEMMA_MODEL = os.environ.get("MAKERTREE_GEMMA_MODEL", "gemma2:2b")
DEFAULT_LLAMA_CPP_HOST = os.environ.get("LLAMA_CPP_HOST", "http://127.0.0.1:8080").rstrip("/")
DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
LLM_BACKEND = os.environ.get("MAKERTREE_LLM_BACKEND", "auto").lower()
GENERATE_TIMEOUT_SEC = 120


def llama_cpp_available(host: str | None = None) -> bool:
    """True if llama.cpp server responds."""
    base = (host or DEFAULT_LLAMA_CPP_HOST).rstrip("/")
    for path in ("/health", "/"):
        try:
            req = urllib.request.Request(f"{base}{path}", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
    return False


def ollama_available(host: str | None = None) -> bool:
    """True if Ollama is running and responds."""
    base = (host or DEFAULT_OLLAMA_HOST).rstrip("/")
    try:
        req = urllib.request.Request(f"{base}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def active_llm_backend() -> str | None:
    """Which local runtime is up: llama_cpp, ollama, or None."""
    if LLM_BACKEND == "llama_cpp":
        return "llama_cpp" if llama_cpp_available() else None
    if LLM_BACKEND == "ollama":
        return "ollama" if ollama_available() else None
    if llama_cpp_available():
        return "llama_cpp"
    if ollama_available():
        return "ollama"
    return None


def local_llm_available() -> bool:
    return active_llm_backend() is not None


def _run_llama_cpp(prompt: str, host: str | None = None) -> tuple[str | None, str | None]:
    base = (host or DEFAULT_LLAMA_CPP_HOST).rstrip("/")
    payload = json.dumps(
        {
            "prompt": prompt,
            "n_predict": 256,
            "temperature": 0.7,
            "stream": False,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/completion",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=GENERATE_TIMEOUT_SEC) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        text = (body.get("content") or body.get("response") or "").strip()
        if not text and isinstance(body.get("choices"), list) and body["choices"]:
            text = (body["choices"][0].get("text") or "").strip()
        if not text:
            return None, "Gemma returned empty text. Check llama.cpp server and model."
        return text, None
    except urllib.error.URLError:
        return None, (
            "llama.cpp server is not running. Start it with your Gemma GGUF, e.g.: "
            "llama-server -m gemma-2-2b-it-Q4_K_M.gguf --port 8080"
        )
    except TimeoutError:
        return None, "Gemma took too long — try a shorter journal entry."
    except (json.JSONDecodeError, KeyError, OSError) as e:
        return None, f"Could not read llama.cpp response: {e}"


def _run_ollama(
    prompt: str, model: str | None = None, host: str | None = None
) -> tuple[str | None, str | None]:
    model = model or DEFAULT_GEMMA_MODEL
    base = (host or DEFAULT_OLLAMA_HOST).rstrip("/")
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 256},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=GENERATE_TIMEOUT_SEC) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        text = (body.get("response") or "").strip()
        if not text:
            return None, "Gemma returned an empty response."
        return text, None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, f"Model '{model}' not found. Run: ollama pull {model}"
        return None, f"Ollama error ({e.code})."
    except urllib.error.URLError:
        return None, f"Ollama is not running. Run: ollama pull {model}"
    except TimeoutError:
        return None, "Gemma took too long — try again."
    except (json.JSONDecodeError, KeyError, OSError) as e:
        return None, f"Could not read Ollama response: {e}"


def run_gemma(
    prompt: str, model: str | None = None, host: str | None = None
) -> tuple[str | None, str | None]:
    """
    Run Gemma locally. Returns (response_text, error_message).
    Tries llama.cpp at `host` first when backend=auto (unless forced to ollama).
    """
    llama_host = (host or DEFAULT_LLAMA_CPP_HOST).rstrip("/")
    if LLM_BACKEND in ("auto", "llama_cpp") and llama_cpp_available(llama_host):
        return _run_llama_cpp(prompt, host=llama_host)
    if LLM_BACKEND in ("auto", "ollama") and ollama_available():
        return _run_ollama(prompt, model=model, host=host)
    if LLM_BACKEND == "llama_cpp":
        return _run_llama_cpp(prompt, host=llama_host)
    return None, (
        "Local Talis is not running. Start **llama.cpp server** with your Gemma GGUF "
        f"(e.g. --port 8086, then set LLAMA_CPP_HOST=http://127.0.0.1:8086). "
        "The app still works without it — Ask Talis will use a gentle fallback."
    )


def gemma_setup_hint() -> str:
    return (
        "**Local Talis (Gemma 2B):** run a **llama.cpp server** with a Gemma 2B GGUF "
        "(you already use llama.cpp), *or* use Ollama — no cloud API key. "
        "See README → Local Talis."
    )


# Backward-compatible alias for the app
ollama_available = local_llm_available
