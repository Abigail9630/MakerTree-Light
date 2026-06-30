"""Central Talis/Gemma service — global toggle, chips, materials context."""

from __future__ import annotations

from typing import Any, Callable, Optional

import streamlit as st

from talis_context import (
    build_gemma_picnic_prompt,
    build_gemma_roots_prompt,
    build_gemma_trunk_prompt,
    build_talis_background,
    build_chip_prompt,
    gather_maker_materials_context,
)
from talis_gemma import run_gemma

# Abigail is still deciding deeper Library + Talis wiring — do not expand Library AI yet.
LIBRARY_TALIS_DEFER = True

CHIP_TARGETS: dict[str, dict[str, str | None]] = {
    "Rain": {
        "page_section": "Rain",
        "field": "talisProjectNotes",
        "widget_key": "Rain_talis_project_notes",
    },
    "Roots": {
        "page_section": "Roots",
        "field": "agentComments",
        "widget_key": "Roots_agent",
    },
    "Trunk": {
        "page_section": "Trunk",
        "field": "agentComments",
        "widget_key": "Trunk_talis",
    },
    "Bark": {
        "page_section": "Bark",
        "field": "solutions",
        "widget_key": "Bark_solutions",
    },
    "Soil": {
        "page_section": "Soil",
        "field": "agentComments",
        "widget_key": "Soil_agent",
    },
    "Leaves": {
        "page_section": "Leaves",
        "field": "fallenLeaves",
        "widget_key": "leaves_fallen",
    },
    "Picnic": {
        "page_section": "Picnic",
        "field": "talisNotes",
        "widget_key": "picnic_talis",
    },
    "Branches": {
        "page_section": None,
        "field": None,
        "widget_key": "note_Branches",
        "notes_history_key": "Branches",
    },
}


def init_talis_prefs() -> None:
    if "talis_enabled" not in st.session_state:
        st.session_state.talis_enabled = True
    if "gemini_enabled" not in st.session_state:
        st.session_state.gemini_enabled = False  # unused — hackathon uses env/secrets only
    if "talis_include_library" not in st.session_state:
        st.session_state.talis_include_library = True
    if "talis_include_legacy" not in st.session_state:
        st.session_state.talis_include_legacy = True


def talis_enabled() -> bool:
    init_talis_prefs()
    return bool(st.session_state.talis_enabled)


def gemini_enabled() -> bool:
    """Not offered in the consumer UI — kept for internal/hackathon use."""
    return False


def _append_reply(current: str, reply: str) -> str:
    reply = reply.strip()
    if not reply:
        return current
    if not current.strip():
        return reply
    return f"{current.rstrip()}\n\n{reply}"


def apply_talis_text_result(request: dict[str, Any], text: str) -> None:
    """Persist Talis output to page_content / notes_history and pending widget."""
    widget_key = request["widget_key"]
    if request.get("notes_history_key"):
        key = request["notes_history_key"]
        existing = st.session_state.notes_history.get(key, "")
        new = _append_reply(existing, text)
        st.session_state.notes_history[key] = new
        st.session_state[f"_pending_{widget_key}"] = new
        return
    page_section = request["page_section"]
    field = request["field"]
    data = st.session_state.page_content.setdefault(page_section, {})
    existing = data.get(field, "")
    new = _append_reply(existing, text)
    data[field] = new
    st.session_state[f"_pending_{widget_key}"] = new


def queue_chip_assist(
    section: str,
    chip: str,
    snapshot: dict[str, Any],
    *,
    widget_key: Optional[str] = None,
    field: Optional[str] = None,
    page_section: Optional[str] = None,
    notes_history_key: Optional[str] = None,
) -> None:
    target = CHIP_TARGETS.get(section, {})
    st.session_state.pending_chip_request = {
        "section": section,
        "chip": chip,
        "snapshot": snapshot,
        "widget_key": widget_key or target.get("widget_key"),
        "field": field or target.get("field"),
        "page_section": page_section if page_section is not None else target.get("page_section"),
        "notes_history_key": notes_history_key or target.get("notes_history_key"),
    }


def run_chip_assist(request: dict[str, Any], llama_host: str) -> tuple[str, Optional[str]]:
    section = request["section"]
    chip = request["chip"]
    snapshot = request.get("snapshot") or {}

    if chip.lower().startswith("no thanks"):
        return "Okay — I'll stay quiet while you write.", None

    from maker_tree_library_ui import get_store

    store = get_store() if st.session_state.get("talis_include_library", True) else None
    include_legacy = st.session_state.get("talis_include_legacy", True)
    include_library = st.session_state.get("talis_include_library", True) and not LIBRARY_TALIS_DEFER

    background = build_talis_background(
        section,
        st.session_state.page_content,
        st.session_state.notes_history,
        store if include_library else None,
        include_library=include_library,
        include_legacy=include_legacy,
    )
    materials = gather_maker_materials_context(st.session_state.page_content)
    prompt = build_chip_prompt(section, chip, background, materials, snapshot)
    return run_gemma(prompt, host=llama_host)


def process_pending_chip_assist(llama_host: str) -> bool:
    """Run queued chip assist before widgets render. Returns True if processed."""
    request = st.session_state.pop("pending_chip_request", None)
    if not request or not talis_enabled():
        return False
    with st.spinner("Talis is thinking…"):
        text, err = run_chip_assist(request, llama_host)
    if err:
        st.warning(err)
        text = f"*(Talis offline — {err})*"
    apply_talis_text_result(request, text)
    return True


def build_ask_prompt(
    section: str,
    background: str,
    snapshot: dict[str, Any],
) -> str:
    materials = gather_maker_materials_context(st.session_state.page_content)
    materials_block = f"\nMaker materials & tools in use:\n{materials}\n"
    bg = background + materials_block

    if section == "Picnic":
        return build_gemma_picnic_prompt(
            snapshot.get("journal", ""),
            snapshot.get("stall_label", "unspecified"),
            snapshot.get("category", ""),
            snapshot.get("maker_profile"),
            bg,
        )
    if section == "Roots":
        return build_gemma_roots_prompt(
            snapshot.get("brainDump", ""),
            snapshot.get("solutions", ""),
            bg,
            chip_request=None,
        )
    if section == "Trunk":
        return build_gemma_trunk_prompt(
            snapshot.get("materialsProcesses", ""),
            snapshot.get("visionInHead", ""),
            bg,
        )
    if section == "Rain":
        from talis_context import build_gemma_rain_prompt

        return build_gemma_rain_prompt(
            snapshot.get("brainDump", ""),
            snapshot.get("talisProjectNotes", ""),
            bg,
        )
    return build_chip_prompt(
        section,
        "Give practical help for this section of the maker tree.",
        bg,
        materials,
        snapshot,
    )
