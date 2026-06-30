"""Talis context — legacy maker journey + Library during transition."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from maker_tree_store import MakerTreeStore

TRANSITION_NOTE = (
    "During transition, Talis can search **both** your maker journey pages and the new Library."
)

LIBRARY_BRANCHES_BY_SECTION: dict[str, list[str]] = {
    "Picnic": ["rain", "projects", "trunk"],
    "Roots": ["rain", "projects"],
    "Trunk": ["trunk", "projects", "rain"],
}

LEGACY_SECTIONS_BY_SECTION: dict[str, list[str]] = {
    "Picnic": ["Rain", "Roots", "Trunk", "Picnic"],
    "Roots": ["Rain", "Roots"],
    "Trunk": ["Roots", "Trunk"],
}

LEGACY_FIELD_LABELS: dict[str, list[tuple[str, str]]] = {
    "Rain": [
        ("brainDump", "Rain dump"),
        ("talisProjectNotes", "Talis project notes"),
    ],
    "Roots": [
        ("brainDump", "Roots brain dump"),
        ("solutions", "Solutions & processes"),
        ("agentComments", "Talis notes"),
    ],
    "Trunk": [
        ("materialsProcesses", "Materials & processes"),
        ("visionInHead", "Vision in head"),
        ("agentComments", "Talis notes"),
    ],
    "Picnic": [
        ("journal", "Picnic journal"),
        ("talisNotes", "Talis notes"),
    ],
}


def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def gather_legacy_tree_context(
    page_content: dict[str, Any],
    notes_history: dict[str, str],
    sections: list[str],
    *,
    max_chars: int = 2400,
) -> str:
    parts: list[str] = []
    total = 0
    for sec in sections:
        data = page_content.get(sec, {})
        for field, label in LEGACY_FIELD_LABELS.get(sec, []):
            chunk = (data.get(field) or "").strip()
            if chunk:
                line = f"**{sec} — {label}:**\n{_clip(chunk, 600)}"
                if total + len(line) > max_chars:
                    return "\n\n".join(parts) + "\n\n*(legacy context truncated)*"
                parts.append(line)
                total += len(line)
        notes = (notes_history.get(sec) or "").strip()
        if notes and sec not in {p.split(" — ")[0].strip("*") for p in parts}:
            line = f"**{sec} — project notes:**\n{_clip(notes, 400)}"
            if total + len(line) <= max_chars:
                parts.append(line)
                total += len(line)
    return "\n\n".join(parts) if parts else "(no maker journey notes yet)"


def gather_library_context(
    store: "MakerTreeStore",
    branch_keys: list[str],
    *,
    max_chars: int = 2000,
    limit_per_branch: int = 12,
) -> str:
    seen: set[str] = set()
    nodes = []
    for branch in branch_keys:
        for node in store.search(branch=branch, limit=limit_per_branch):
            if node.id in seen:
                continue
            seen.add(node.id)
            nodes.append(node)
    nodes.sort(key=lambda n: n.updated_at, reverse=True)

    lines: list[str] = []
    total = 0
    for node in nodes:
        tag_str = f" [{', '.join(node.tags)}]" if node.tags else ""
        line = f"[Library/{node.branch}] {node.title or 'Untitled'}{tag_str}\n{_clip(node.text, 350)}"
        if total + len(line) > max_chars:
            lines.append("*(Library context truncated)*")
            break
        lines.append(line)
        total += len(line)
    return "\n\n".join(lines) if lines else "(no Library notes yet)"


def build_talis_background(
    section: str,
    page_content: dict[str, Any],
    notes_history: dict[str, str],
    store: Optional["MakerTreeStore"],
    *,
    include_library: bool = True,
    include_legacy: bool = True,
) -> str:
    blocks: list[str] = []
    materials = gather_maker_materials_context(page_content)
    if materials.strip():
        blocks.append(f"### Materials & tools in use\n{materials}")
    if include_legacy:
        sections = LEGACY_SECTIONS_BY_SECTION.get(section, [section])
        legacy = gather_legacy_tree_context(page_content, notes_history, sections)
        blocks.append(f"### Maker journey pages\n{legacy}")
    if include_library and store is not None:
        branches = LIBRARY_BRANCHES_BY_SECTION.get(section, ["rain", "trunk", "projects"])
        library = gather_library_context(store, branches)
        blocks.append(f"### Library\n{library}")
    if not blocks:
        return "(no background context selected)"
    return "\n\n".join(blocks)


def gather_maker_materials_context(page_content: dict[str, Any]) -> str:
    """Tools and materials the maker is working with — Grove, Trunk, Roots."""
    lines: list[str] = []
    picnic = page_content.get("Picnic", {})
    if picnic.get("makerCategory"):
        lines.append(f"Primary craft: {picnic['makerCategory']}")
    if picnic.get("profileTools", "").strip():
        lines.append(f"Profile tools: {picnic['profileTools'].strip()}")
    trunk = page_content.get("Trunk", {})
    if trunk.get("materialsProcesses", "").strip():
        lines.append(f"Trunk materials/processes:\n{_clip(trunk['materialsProcesses'], 500)}")
    roots = page_content.get("Roots", {})
    if roots.get("brainDump", "").strip():
        lines.append(f"Roots ideas (may mention materials):\n{_clip(roots['brainDump'], 400)}")
    return "\n".join(lines) if lines else "(not specified yet — infer from their words if needed)"


def build_gemma_rain_prompt(
    brain_dump: str,
    talis_project_notes: str,
    background_context: str,
) -> str:
    return f"""You are Talis, a gentle female maker mentor — warm, practical, first-person.

The maker is at **Rain** — an unfiltered brain dump.

Background:
{background_context}

Their rain dump:
{brain_dump.strip() or "(empty)"}

Existing Talis project notes (if any):
{talis_project_notes.strip() or "(none)"}

IMPORTANT — Rain rules:
- **Recommend groupings only.** Suggest what might belong under **Roots** (product/vision work) vs **Picnic** (daily life, rest, fears).
- **Do NOT** say you moved, filed, or saved anything. The maker moves items manually.
- Format suggestions as numbered lists under **Roots** and **Picnic** headings when sorting.
- Never bombard with questions.

Respond helpfully in plain text."""


def build_gemma_roots_prompt(
    brain_dump: str,
    solutions: str,
    background_context: str,
    *,
    chip_request: str | None = None,
) -> str:
    chip_line = f"\nThey tapped for help with: {chip_request}\n" if chip_request else ""
    return f"""You are Talis, a gentle female maker mentor — warm, practical, first-person.

The maker is at **Roots** — grounding ideas from Rain.
{chip_line}
Background:
{background_context}

Roots brain dump:
{brain_dump.strip() or "(empty)"}

Solutions & processes:
{solutions.strip() or "(empty)"}

IMPORTANT — Roots rules:
- **Actively group ideas** by **material**, **process**, and **tool** when you can see those threads.
- Name competitive advantage when visible. Help pick one thread if there are too many.
- At most 1–2 gentle questions only if something needs unlocking.
- Invite "what do you see in your head?" when relevant.

Respond in clear, grouped text (use short headings like Material / Process / Tool when helpful)."""


def build_chip_prompt(
    section: str,
    chip: str,
    background_context: str,
    materials_context: str,
    snapshot: dict[str, Any],
) -> str:
    if section == "Rain":
        return f"""You are Talis, a gentle maker mentor. The maker tapped: "{chip}"

Materials & tools context:
{materials_context}

Background:
{background_context}

Rain dump:
{snapshot.get("brainDump", "").strip() or "(empty)"}

Rules: Recommend groupings only for Roots vs Picnic. Do NOT claim anything was moved or saved. Use **Roots** and **Picnic** headings with numbered lists when sorting."""

    if section == "Roots":
        return build_gemma_roots_prompt(
            snapshot.get("brainDump", ""),
            snapshot.get("solutions", ""),
            background_context,
            chip_request=chip,
        )

    page_text = "\n".join(
        f"{k}: {_clip(str(v), 400)}"
        for k, v in snapshot.items()
        if v and str(v).strip()
    )
    return f"""You are Talis, a gentle female maker mentor — warm, practical, first-person.

Section: {section}
They tapped: "{chip}"

Materials & tools in use:
{materials_context}

Background:
{background_context}

Current page content:
{page_text or "(empty)"}

Answer the chip request directly and practically. Write text they can paste into their notes — no markdown fences."""


def build_gemma_picnic_prompt(
    journal: str,
    stall_label: str,
    category: str,
    maker_profile: dict | None,
    background_context: str,
) -> str:
    profile = maker_profile or {}
    tools = profile.get("tools", "not specified")
    materials = profile.get("materials", "not specified")
    experience = profile.get("experience", "not specified")
    return f"""You are Talis, a gentle female maker mentor under a sycamore tree — not a therapist, not corporate.

Maker primary craft: {category or "general maker"}
Tools: {tools}
Materials: {materials}
Experience: {experience}

They sat down at the Picnic because: {stall_label}

Background from their tree and Library (may be partial):
{background_context}

Guardrails:
- Never diagnose. Never bombard with questions. At most ONE gentle question OR one reflection.
- Normalize stall (imposter, fear, over-excitement, skill gaps) without toxic positivity.
- Suggest ONE place in the tree if helpful: Rain (dump), Roots (ground idea), Trunk (skill/tools), Bark (visibility), Branches (sales), or stay at Picnic.
- Tailor language to their craft ({category}).
- First person, warm, no "we/our", no "magic".

What they wrote at Picnic:
{journal.strip() or "(quiet — just sitting)"}

Respond in 3–5 short sentences. End with an optional single question only if it unlocks something."""


def build_gemma_trunk_prompt(
    materials: str,
    vision: str,
    background_context: str,
) -> str:
    return f"""You are Talis, a gentle female maker mentor — warm, practical, first-person, not corporate.

The maker is at **Trunk** — tools, materials, workflows, and the picture in their head before making.

Background from their tree and Library (may be partial):
{background_context}

Materials & processes on this page:
{materials.strip() or "(empty)"}

What they see in their head:
{vision.strip() or "(empty)"}

Guardrails:
- Help with workflow steps, tool lists, and realistic next actions — not perfection.
- If something is disappointing: ask gently if they are unhappy with how it works or appears; offer books, resources, or a master craftsperson when you cannot answer from here.
- At most ONE question unless a second truly unlocks the workflow.

Respond in 4–6 short sentences. Practical and grounded."""
