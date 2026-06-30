"""Shared Ask Talis controls — global toggle, chips, Gemini assist."""

from __future__ import annotations

from typing import Any, Callable, Optional

import streamlit as st

from talis_context import build_talis_background
from talis_gemma import gemma_setup_hint, llama_cpp_available, ollama_available, run_gemma
from talis_service import (
    LIBRARY_TALIS_DEFER,
    build_ask_prompt,
    init_talis_prefs,
    queue_chip_assist,
    talis_enabled,
)


def flush_pending_talis_widget(widget_key: str, default: str) -> str:
    pending = f"_pending_{widget_key}"
    if pending in st.session_state:
        value = st.session_state.pop(pending)
        st.session_state[widget_key] = value
        return value
    return default


def render_manual_badge() -> None:
    if talis_enabled():
        return
    st.markdown(
        '<span class="manual-mode-badge">Manual</span>',
        unsafe_allow_html=True,
    )


def render_app_settings(get_llama_cpp_host: Callable[[], str]) -> None:
    init_talis_prefs()
    with st.expander("Settings", expanded=False):
        st.session_state.talis_enabled = st.toggle(
            "Talis (local Gemma)",
            value=st.session_state.talis_enabled,
            key="settings_talis_enabled",
            help="Off = Manual mode. Chips and Ask Talis are disabled.",
        )
        if not talis_enabled():
            st.info("**Manual mode** — Talis is off. Everything works by hand.")
        else:
            st.caption(gemma_setup_hint())
        st.text_input(
            "llama.cpp server URL (local Talis)",
            value=get_llama_cpp_host(),
            key="llama_cpp_host",
            placeholder="http://127.0.0.1:8086",
        )
        if LIBRARY_TALIS_DEFER:
            st.caption(
                "Library + Talis: deeper integration paused while Abigail reviews — journey pages are wired first."
            )


def render_talis_backend_caption(llama_host: str) -> None:
    if not talis_enabled():
        st.caption("Manual mode — turn Talis on in **Settings** to use Ask Talis.")
        return
    if llama_cpp_available(llama_host):
        st.caption(f"Talis (Gemma 2B, local) is ready — llama.cpp at `{llama_host}`.")
    elif ollama_available():
        st.caption("Talis (Gemma 2B, local) is ready — Ollama.")
    else:
        st.caption(gemma_setup_hint())


def render_talis_chips(
    section: str,
    chips: list[str],
    snapshot: dict[str, Any],
    *,
    num_cols: int = 2,
) -> None:
    st.markdown(f"**Ways Talis can help**")
    if talis_enabled():
        st.caption("Tap one — Talis writes into your notes.")
    else:
        st.caption("Manual mode — chips are off. Turn Talis on in **Settings**.")
    chip_cols = st.columns(num_cols)
    disabled = not talis_enabled()
    for i, chip in enumerate(chips):
        with chip_cols[i % num_cols]:
            if st.button(
                chip,
                key=f"chip_{section}_{i}",
                disabled=disabled,
                use_container_width=True,
            ):
                queue_chip_assist(section, chip, snapshot)
                st.rerun()


def run_ask_talis(
    section: str,
    *,
    llama_host: str,
    snapshot: dict[str, Any],
    widget_key: str,
    save_to_page: Callable[[str], None],
    fallback: Callable[[], str],
) -> None:
    render_talis_backend_caption(llama_host)
    if not talis_enabled():
        return
    if st.button("Ask Talis", use_container_width=True, key=f"ask_talis_{section}"):
        from maker_tree_library_ui import get_store

        store = get_store() if st.session_state.get("talis_include_library", True) else None
        include_library = (
            st.session_state.get("talis_include_library", True) and not LIBRARY_TALIS_DEFER
        )
        background = build_talis_background(
            section,
            st.session_state.page_content,
            st.session_state.notes_history,
            store if include_library else None,
            include_library=include_library,
            include_legacy=st.session_state.get("talis_include_legacy", True),
        )
        prompt = build_ask_prompt(section, background, snapshot)
        with st.spinner("Talis is thinking…"):
            text, err = run_gemma(prompt, host=llama_host)
        if err:
            st.warning(err)
            result = fallback() + f"\n\n*(Gemma offline — gentle fallback. {err})*"
        else:
            result = text or fallback()
        save_to_page(result)
        st.session_state[f"_pending_{widget_key}"] = result
        st.rerun()
