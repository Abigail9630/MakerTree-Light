import streamlit as st
import os
import base64
import csv
import io
import re
from datetime import datetime
from pathlib import Path

# Gemini integration for Xprize-required API call (one call in Roots for parsing/guardrails)
# Local fallback remains for the main experience.
try:
    import google.generativeai as genai
except ImportError:
    genai = None

st.set_page_config(page_title="Maker Tree", layout="wide", initial_sidebar_state="collapsed")

# Sycamore Grove onboarding — first launch + optional return from Soil / Picnic
grove_flag = Path.home() / ".maker_tree_grove_completed"
GROVE_FORM_URL = "https://forms.gle/YOUR_FORM_ID_HERE"  # replace when Google Form is live

if "grove_completed" not in st.session_state:
    # New makers (no flag file) see the Grove before Talis; returning makers skip unless they choose to go back
    st.session_state.grove_completed = grove_flag.exists()
if "grove_form_stage" not in st.session_state:
    st.session_state.grove_form_stage = 1
if "return_to_grove" not in st.session_state:
    st.session_state.return_to_grove = False

# Font improvements: heavier weights, larger base size for readability on mobile/dark themes
# Using Google fonts (same as HTML version) + system fallback. Increase size/weight.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800&family=Instrument+Serif:wght@600;700&display=swap');

html, body, [class*="css"], .stMarkdown, .stTextArea, .stButton>button {
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    font-size: 19px !important;  /* bumped for phone/dark readability */
    font-weight: 500 !important;
    line-height: 1.7 !important;
}

h1, h2, h3, .stSubheader, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'Inter', system-ui, sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.2em !important;
}

/* Logo header already has inline heavier style */

/* Basic dark theme support for phone/dark mode users */
@media (prefers-color-scheme: dark) {
    html, body, [class*="css"] {
        background-color: #1f242e !important;
        color: #e8e8e8 !important;
    }
    .stTextArea textarea, .stTextInput input {
        background-color: #2c3340 !important;
        color: #e8e8e8 !important;
        border-color: #4a5568 !important;
    }
    .stButton>button {
        background-color: #166534 !important;
        color: white !important;
    }
}

/* Mobile-first: hide sidebar — main-page branch buttons are the primary nav */
section[data-testid="stSidebar"],
button[data-testid="stSidebarCollapsedControl"],
button[data-testid="collapsedControl"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# Central tree image for the main page.
# Uses the real central-tree.jpg from assets/images so the beautiful sycamore anchors the experience.
script_dir = os.path.dirname(os.path.abspath(__file__))
tree_image_path = os.path.join(script_dir, "assets", "images", "central-tree.jpg")
if not os.path.exists(tree_image_path):
    tree_image_path = None  # Will show graceful fallback in UI

# Gemini-generated circular logo (replaces all small 🌳 emoji trees at top of every page)
logo_path = os.path.join(script_dir, "assets", "images", "maker-tree-logo.png")
logo_b64 = None
if os.path.exists(logo_path):
    with open(logo_path, "rb") as img_file:
        logo_b64 = base64.b64encode(img_file.read()).decode()

# Per-section banner image + crop focus (object-position), matching index.html h-56 banners.
SECTION_BANNERS = {
    "Rain": ("assets/reference-photos/Rain.jpg", "center 50%"),
    "Roots": ("assets/reference-photos/20240609_140622.jpg", "center center"),
    "Trunk": ("assets/reference-photos/Trunk.jpg", "center 45%"),
    "Branches": ("assets/reference-photos/Branches.jpg", "center 45%"),
    "Bark": ("assets/reference-photos/Bark.jpg", "center center"),
    "Leaves": ("assets/reference-photos/Leaves.jpg", "center 45%"),
    "Soil": ("assets/reference-photos/Soil.jpg", "center 45%"),
    "Picnic": ("assets/images/central-tree.jpg", "48% 96%"),
}


def render_app_header() -> None:
    """MakerTree logo + title — tap either to return to the main tree page."""
    if logo_b64:
        st.markdown(
            f"""
            <style>
            .st-key-nav_home_logo button {{
                background: url('data:image/png;base64,{logo_b64}') center/cover no-repeat !important;
                width: 48px !important;
                height: 48px !important;
                min-height: 48px !important;
                border: 2px solid #166534 !important;
                border-radius: 50% !important;
                padding: 0 !important;
                box-shadow: 0 1px 3px rgba(0,0,0,0.15) !important;
            }}
            .st-key-nav_home_logo button p {{
                display: none !important;
            }}
            .st-key-nav_home_title button {{
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                color: #166534 !important;
                font-size: 28px !important;
                font-weight: 700 !important;
                padding: 0 !important;
                text-align: left !important;
            }}
            .st-key-nav_home_title button:hover,
            .st-key-nav_home_title button:focus {{
                color: #14532d !important;
                background: transparent !important;
                border: none !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

    logo_col, title_col, _ = st.columns([0.09, 0.35, 0.56], vertical_alignment="center")
    go_home = False
    with logo_col:
        if logo_b64 and st.button(
            " ",
            key="nav_home_logo",
            help="Back to the main tree",
            use_container_width=True,
        ):
            go_home = True
    with title_col:
        if st.button(
            "MakerTree",
            key="nav_home_title",
            help="Back to the main tree",
        ):
            go_home = True

    if go_home:
        st.session_state["pending_section"] = "Welcome"
        st.rerun()


def complete_grove() -> None:
    """Mark Grove onboarding done and continue to the tree."""
    grove_flag.touch()
    st.session_state.grove_completed = True
    st.session_state.return_to_grove = False
    st.session_state.grove_form_stage = 1


def request_return_to_grove() -> None:
    """Send the maker back to the Grove (new tools, channels, materials)."""
    st.session_state.grove_completed = False
    st.session_state.return_to_grove = True
    st.session_state.grove_form_stage = 1


def render_back_to_tree_button(section: str) -> None:
    """Bottom of each subpage — logo at top also returns home."""
    st.divider()
    if st.button(
        "← Back to the tree (main page)",
        use_container_width=True,
        key=f"back_to_tree_{section}",
    ):
        st.session_state["pending_section"] = "Welcome"
        st.rerun()


def render_return_to_grove_button(key_suffix: str) -> None:
    """Soil / Picnic — update maker profile when tools or channels change."""
    st.divider()
    st.caption(
        "New tools, materials, or sales channels along the way? "
        "Walk back through the Sycamore Grove and update your maker profile."
    )
    if st.button(
        "🌳 Return to the Sycamore Grove",
        key=f"return_grove_{key_suffix}",
        use_container_width=True,
    ):
        request_return_to_grove()
        st.rerun()


def render_sycamore_grove() -> None:
    """First-screen onboarding (Olive): intro → form → Let's grow."""
    returning = st.session_state.return_to_grove
    st.title("Welcome to the Sycamore Grove" if not returning else "The Sycamore Grove")

    grove_image = os.path.join(
        script_dir, "assets", "reference-photos", "Gemini_Generated_Image_SycamoreGrove.jpg"
    )
    if os.path.exists(grove_image):
        st.image(grove_image, use_container_width=True)
    else:
        st.warning("Sycamore Grove image not found.")

    st.markdown(
        """
        <div style="text-align: center; margin: 24px 0;">
            <p style="font-size: 1.15rem; line-height: 1.7;">
                Step into the grove. The air is clear and cool. In the distance, mountains rise against the sky.
                Beneath your feet, the damp earth smells of pine and possibility.
                This is where your ideas begin to take root.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.grove_form_stage == 1:
        st.markdown(
            "Tell Talis about your tools, materials, style, and sales channels — "
            "so she can meet you where you are."
        )
        st.link_button(
            "Enter the Sycamore Grove (open form in new tab)",
            GROVE_FORM_URL,
            use_container_width=True,
        )
        if st.button(
            "I've opened the form — continue",
            use_container_width=True,
            key="grove_advance_stage",
        ):
            st.session_state.grove_form_stage = 2
            st.rerun()
        if not returning and st.button(
            "Continue to the Tree (skip for now)",
            use_container_width=True,
            key="grove_skip",
        ):
            complete_grove()
            st.rerun()
    else:
        st.markdown(
            """
            <div style="text-align: center; margin: 20px 0;">
                <p style="font-size: 1.12rem; line-height: 1.7;">
                    Thank you for planting your roots here. Whether you filled out every field or simply breathed
                    in the mountain air — you belong in this grove. Talis is waiting under the tree.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.link_button(
            "Open the Grove form again",
            GROVE_FORM_URL,
            use_container_width=True,
        )
        if st.button("Let's grow — continue to the tree", use_container_width=True, key="grove_lets_grow"):
            complete_grove()
            st.rerun()


def render_section_banner(section: str) -> None:
    """Render a slim cropped banner (like index.html project view)."""
    rel_path, object_pos = SECTION_BANNERS.get(section, (None, "center 20%"))
    if rel_path:
        banner_file = os.path.join(script_dir, rel_path)
    else:
        banner_file = tree_image_path
        object_pos = "center 20%"

    if not banner_file or not os.path.exists(banner_file):
        return

    with open(banner_file, "rb") as img_file:
        b64 = base64.b64encode(img_file.read()).decode()
    st.markdown(
        f"""
        <div style="
            width: 100%;
            height: 140px;
            overflow: hidden;
            border-radius: 12px;
            margin-bottom: 0.5rem;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        ">
            <img src="data:image/jpeg;base64,{b64}"
                 style="width:100%; height:100%; object-fit: cover; object-position: {object_pos}; display: block;" />
        </div>
        """,
        unsafe_allow_html=True,
    )


def parse_with_gemini(brain_dump: str, api_key: str) -> str:
    """Call Gemini for Roots parsing: competitive advantage + gentle guardrails."""
    if genai is None:
        return "Install google-generativeai first: pip install google-generativeai"
    if not api_key:
        return "Please provide a Gemini API key (from Google AI Studio)."
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')  # fast and sufficient for this
        prompt = f"""You are a gentle, wise homesteading agent helping plastic-free makers turn brain dumps into real products. Stay in first-person warm storytelling voice (no "we/our", no "magic").

Parse this brain dump:
1. Extract main product ideas.
2. For each, identify the competitive advantage (unique homestead voice, plastic-free materials, edge in market).
3. Only suggest 1-2 gentle questions if you detect hesitation (words like "not sure", "maybe", "don't know", "stuck", "overwhelmed").
4. If an idea seems about to be disregarded, MUST include this exact question: "Is there a tool/material/skill that you have not used before and want to try?"

Keep responses short, encouraging, practical. Format as:

**Ideas & Competitive Advantages:**
- Idea 1: ...
  Advantage: ...

**Gentle Questions (only if needed):**
- ...

Brain dump:
{brain_dump}"""
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Gemini call failed: {str(e)}. Check your API key and quota."

# Session state for navigation and persistent notes
if 'current_section' not in st.session_state:
    st.session_state.current_section = "Welcome"
if 'notes_history' not in st.session_state:
    st.session_state.notes_history = {
        "Rain": "Your rain dump goes at the top. Talis Project Notes below show how she sorted toward Roots and Picnic.",
        "Roots": "Parsing stage. Competitive advantage clarified. Gentle agent questions only when helpful.",
        "Trunk": "Core tools, materials, and current experience. Turn your ideas into workflows and final products.",
        "Branches": "Sales channels — Etsy, website, markets, social. Some makers tend one, others several.",
        "Bark": "Storytelling, photography composition, social voice. Sycamore bark peels and renews; older successes build foundation.",
        "Leaves": "Actual products and sales. Feedback falls to soil. Dry leaves signal refresh or discount.",
        "Soil": "Nutrient base. Reviews, data, fallen leaves prevent mold and enrich the next rain. Small non-threatening steps.",
        "Picnic": "Peaceful inner-work space on the quilt under the tree. Fears, imposter feelings, joy, rest, character growth. No pressure.",
    }

# Structured page content replicating the rich index.html for Rain, Roots, Bark, Soil
# (banner + Brain Dump + Solutions & Processes + Agent + Current Project Notes structure)
if 'page_content' not in st.session_state:
    st.session_state.page_content = {
        "Rain": {
            "firstHeader": "Rain — Brain Dump",
            "brainDump": "",
            "talisProjectNotes": "",
            "talisCorrections": "",
            "agentComments": (
                "I read your rain and sort gently — I never bombard you with questions.\n\n"
                "When sorting, I separate vision toward Roots and daily life toward Picnic.\n"
                "I stay warm, grounded, first-person. At most 1–2 questions — only if something genuinely needs unlocking."
            ),
        },
        "Trunk": {
            "materialsProcesses": "",
            "visionInHead": "",
            "agentComments": "",
        },
        "Leaves": {
            "fallenLeaves": "",
            "inactiveProducts": "",
        },
        "Roots": {
            "firstHeader": "Raw Ideas",
            "brainDump": "Roots\n\nWhere the real grounding happens. This is where the agent steps in to help parse the rain into clear, usable ideas. We sort, research, identify competitive advantage, decide on materials, price points, and processes. The roots keep the whole tree stable. You can click directly here if you've already dumped in the rain.",
            "solutions": "",
            "agentComments": "Guardrails for Talis in Roots:\n- If 'I don't know what to make, too many ideas': 'Tell me everything you love. How could you make these differently from what you've seen before?'\n- If tired of a material: 'What new material excites you even if it doesn't seem profitable?'\n- For combinations: 'How to combine without degrading each? Need new tools?'\n- For many materials: 'Keep separate or combine?'\n\nAlways ask before leaving: 'What do you see in your head?' Define each: material, tools, how displayed (lighting/color/atmosphere), who for, best setting.",
        },
        "Bark": {
            "firstHeader": "Social Media channels Current",
            "brainDump": "Storytelling, social media, and the living outer layer that carries your voice into the world. Sycamore bark peels and renews; older successes build foundation.",
            "solutions": "",
            "agentComments": "Guardrails for Talis in Bark:\nIf burned out on social: Suggest focus on 1-2 platforms. Offer help with copy, stories, hashtags, workflows.\n- Instagram: new + visual story\n- Pinterest: products + URLs/inspiration\n- Facebook: maker life + benefits of handcrafted\n- Tumblr: image + process (no shop links)\n- TikTok: live + process + humor (TikTok shop optional)\n- Substack: feeling behind product (how it feels to make/use)\n- X: how products improve the world",
        },
        "Soil": {
            "firstHeader": "Enriched Soil",
            "brainDump": "",
            "solutions": "",
            "agentComments": "",
        },
    }

# Talis quick-help buttons per section (label avoids "prompt chips" — makers are AI-shy)
TALIS_HELP_LABEL = "Ways Talis can help"
TALIS_HELP_CAPTION = "Tap one if you'd like Talis to pick up that thread."

talis_chips = {
    "Rain": [
        "Sort my rain — vision vs Picnic list",
        "What here could become a product?",
        "No thanks — just let me write",
    ],
    "Roots": [
        "List my main materials",
        "Describe my style and aesthetic",
        "What are my best selling points?",
        "Help me identify the competitive advantage",
        "What do you see in your head for this?",
        "What materials and tools come to mind?",
    ],
    "Bark": [
        "Help me storyboard a TikTok video",
        "Suggest post copy for Instagram",
        "Create hashtags for this product",
        "Help with Pinterest description",
        "Draft a Substack feeling piece",
    ],
    "Soil": [
        "Summarize customer feedback",
        "What are my best sellers?",
        "Which items should I discount?",
        "Help me review inventory",
    ],
    "Trunk": [
        "List tools I need for this",
        "Help with workflow steps",
        "Something isn't working — help me",
        "Suggest a different material or technique",
    ],
    "Branches": [
        "Suggest new sales channels",
        "Help price this item",
        "Ideas for in-person events",
        "How to add more branches?",
    ],
    "Leaves": [
        "Where to sell inactive products",
        "Do you still enjoy making this item?",
        "Review sales performance",
        "Suggest discounts or flash sales",
        "Analyze what didn't sell",
        "Ideas to refresh slow leaves",
    ],
    "Picnic": [
        "Help me reflect on why I make",
        "What brings me joy in this work?",
        "What feels heavy or wonderful?",
    ],
}


RAIN_TALIS_PROJECT_NOTES_STARTER = """Talis sorts your vision toward Roots and daily life toward Picnic. This is her sorted list — numbered so you can see what she noticed. (This is not another brain dump.)

**Roots**
1.

**Picnic**
1.
"""


def _section_from_talis_notes(notes: str, section: str) -> str:
    """Extract numbered list text under a **Roots** or **Picnic** heading."""
    match = re.search(
        rf"\*\*{section}\*\*\s*\n(.*?)(?=\n\*\*|\Z)",
        notes,
        re.DOTALL | re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def _migrate_rain_talis_notes(data: dict) -> str:
    """Build Talis Project Notes from new or legacy Rain fields."""
    if data.get("talisProjectNotes", "").strip():
        return data["talisProjectNotes"]

    roots_legacy = data.get("sortedVision", "").strip()
    picnic_legacy = data.get("sortedPicnic", "").strip()
    if roots_legacy or picnic_legacy:
        lines = [
            "Talis sorts your vision toward Roots and daily life toward Picnic. "
            "This is her sorted list — numbered so you can see what she noticed.",
            "",
            "**Roots**",
        ]
        roots_items = [ln.strip().lstrip("•").strip() for ln in roots_legacy.splitlines() if ln.strip()]
        if roots_items:
            lines.extend(f"{i}. {item}" for i, item in enumerate(roots_items, 1))
        else:
            lines.append("1.")
        lines.extend(["", "**Picnic**"])
        picnic_items = [ln.strip().lstrip("•").strip() for ln in picnic_legacy.splitlines() if ln.strip()]
        if picnic_items:
            lines.extend(f"{i}. {item}" for i, item in enumerate(picnic_items, 1))
        else:
            lines.append("1.")
        return "\n".join(lines)

    return RAIN_TALIS_PROJECT_NOTES_STARTER


def _rain_page_data() -> dict:
    """Rain page fields with backward-compatible keys."""
    data = st.session_state.page_content.setdefault("Rain", {})
    data.setdefault("talisProjectNotes", _migrate_rain_talis_notes(data))
    data.setdefault("talisCorrections", "")
    return data


def _save_rain_fields(
    brain: str,
    talis: str,
    talis_project_notes: str,
    talis_corrections: str,
) -> None:
    st.session_state.page_content["Rain"]["brainDump"] = brain
    st.session_state.page_content["Rain"]["agentComments"] = talis
    st.session_state.page_content["Rain"]["talisProjectNotes"] = talis_project_notes
    st.session_state.page_content["Rain"]["talisCorrections"] = talis_corrections

    picnic_block = _section_from_talis_notes(talis_project_notes, "Picnic")
    if picnic_block:
        picnic_existing = st.session_state.notes_history.get("Picnic", "")
        picnic_copy = f"**From Rain (Talis sorted for Picnic):**\n{picnic_block}"
        if picnic_copy not in picnic_existing:
            st.session_state.notes_history["Picnic"] = (
                f"{picnic_existing}\n\n{picnic_copy}".strip()
                if picnic_existing.strip()
                else picnic_copy
            )


def render_rain_page() -> None:
    """Rain — unfiltered dump; Talis sorts vision (Roots) vs daily (Picnic)."""
    if "rain_empty_nudge" not in st.session_state:
        st.session_state.rain_empty_nudge = False

    data = _rain_page_data()
    st.subheader(data.get("firstHeader", "Rain — Brain Dump"))
    st.caption(
        "Ideas, thoughts, hopes, vision, and mental sketches — **no holds barred**. "
        "A toothache, new rocking chair plans, and a CNC machine can all land in one heap."
    )

    brain = st.text_area(
        "Rain dump",
        value=data.get("brainDump", ""),
        height=280,
        key="Rain_brain",
        label_visibility="collapsed",
        placeholder=(
            "Let it rain… Dump everything here. No judgment. "
            "Toothaches, thread counts, wood varnish, fairy door hinges, "
            "half-formed product notions, random hopes — all of it."
        ),
    )

    brain_empty = not brain.strip()
    if st.session_state.rain_empty_nudge and brain_empty:
        st.info(
            "Your rain is still open — pour whatever is on your mind above when you're ready. "
            "Nothing has to be perfect."
        )

    st.markdown("**Talis**")
    talis = st.text_area(
        "Talis",
        value=data.get("agentComments", ""),
        height=120,
        key="Rain_talis",
        label_visibility="collapsed",
        placeholder="Talis may leave a brief, warm note here after sorting — not a second brain dump.",
    )

    st.markdown(f"**{TALIS_HELP_LABEL}**")
    st.caption(TALIS_HELP_CAPTION)
    chip_cols = st.columns(3)
    for i, chip in enumerate(talis_chips["Rain"]):
        with chip_cols[i % 3]:
            if st.button(chip, key=f"chip_Rain_{i}"):
                curr = st.session_state.page_content["Rain"]["agentComments"]
                new = curr + "\n\n" + chip if curr.strip() else chip
                st.session_state.page_content["Rain"]["agentComments"] = new
                st.rerun()

    st.divider()
    st.markdown("**Talis Project Notes**")
    st.caption(
        "Talis sorts your vision toward Roots and daily life toward Picnic. "
        "This is where she lists what she noticed — numbered under each heading. "
        "You can edit if she misplaced something."
    )
    talis_project_notes = st.text_area(
        "Talis Project Notes",
        value=data.get("talisProjectNotes", RAIN_TALIS_PROJECT_NOTES_STARTER),
        height=220,
        key="Rain_talis_project_notes",
        label_visibility="collapsed",
    )

    st.markdown("**Corrections for Talis**")
    st.caption(
        "If something landed in the wrong place, or you want Talis to sort differently, say so here. "
        "One box — not a long chat — keeps the light app calm."
    )
    talis_corrections = st.text_area(
        "Corrections for Talis",
        value=data.get("talisCorrections", ""),
        height=100,
        key="Rain_talis_corrections",
        label_visibility="collapsed",
        placeholder=(
            "For example: Move the toothache to Picnic only. "
            "The fairy door hinge idea is product work — keep it under Roots."
        ),
    )

    if st.button("Save Rain page", use_container_width=True):
        _save_rain_fields(brain, talis, talis_project_notes, talis_corrections)
        st.success("Saved. Talis Project Notes show her sort; Picnic items copy to Picnic when listed.")

    # Move on to Roots — one gentle nudge if dump is empty (no double highlight)
    if brain_empty and not st.session_state.rain_empty_nudge:
        roots_label = "Do you want to finish your Brain Dump?"
    elif brain_empty:
        roots_label = "Move on to Roots anyway"
    else:
        roots_label = "Move on to Roots"

    if st.button(roots_label, use_container_width=True, key="rain_to_roots"):
        if brain_empty and not st.session_state.rain_empty_nudge:
            st.session_state.rain_empty_nudge = True
            st.rerun()
        else:
            _save_rain_fields(brain, talis, talis_project_notes, talis_corrections)
            st.session_state.rain_empty_nudge = False
            roots_block = _section_from_talis_notes(talis_project_notes, "Roots")
            if roots_block:
                roots_data = st.session_state.page_content.setdefault("Roots", {})
                from_rain = f"**From Rain (Talis sorted for Roots):**\n{roots_block}"
                existing = roots_data.get("brainDump", "")
                if from_rain not in existing:
                    roots_data["brainDump"] = (
                        f"{existing}\n\n{from_rain}".strip() if existing.strip() else from_rain
                    )
            st.session_state["pending_section"] = "Roots"
            st.rerun()


def _trunk_page_data() -> dict:
    data = st.session_state.page_content.setdefault("Trunk", {})
    if not data.get("materialsProcesses", "").strip():
        legacy = st.session_state.notes_history.get("Trunk", "")
        if legacy.strip():
            data["materialsProcesses"] = legacy
    data.setdefault("visionInHead", "")
    data.setdefault("agentComments", "")
    return data


def render_trunk_page() -> None:
    """Trunk — materials, processes, and the mental picture before making."""
    data = _trunk_page_data()
    st.subheader("Shop and Tools")
    st.caption("Materials, processes and procedures to create what you saw in the Rain.")

    materials = st.text_area(
        "Materials and processes",
        value=data.get("materialsProcesses", ""),
        height=220,
        key="Trunk_materials",
        label_visibility="collapsed",
        placeholder=(
            "Core tools, materials, and current experience. "
            "Turn your ideas into workflows and final products."
        ),
    )

    st.markdown("**Talis**")
    talis = st.text_area(
        "Talis",
        value=data.get("agentComments", ""),
        height=120,
        key="Trunk_talis",
        label_visibility="collapsed",
        placeholder="Talis may leave a brief note here — practical, grounded, no pressure.",
    )

    if "Trunk" in talis_chips:
        st.markdown(f"**{TALIS_HELP_LABEL}**")
        st.caption(TALIS_HELP_CAPTION)
        chip_cols = st.columns(2)
        for i, chip in enumerate(talis_chips["Trunk"]):
            with chip_cols[i % 2]:
                if st.button(chip, key=f"chip_Trunk_{i}"):
                    curr = st.session_state.page_content["Trunk"]["agentComments"]
                    new = curr + "\n\n" + chip if curr.strip() else chip
                    st.session_state.page_content["Trunk"]["agentComments"] = new
                    st.rerun()

        st.markdown(
            "When a make is disappointing or not working the way you pictured, Talis may gently ask: "
            "*Are you disappointed or unhappy with how this item works or appears?* "
            "If yes — *How can I help?* "
            "When she cannot answer from here, she will point you toward books, online resources, "
            "your library, or a Master Craftsperson."
        )

    st.divider()
    st.markdown("**What do you see in your head?**")
    st.caption(
        "The goal of every maker — the picture in your mind before it exists in your hands. "
        "Material, tools, lighting, color, atmosphere, who it is for, how it is best displayed."
    )
    vision = st.text_area(
        "What do you see in your head?",
        value=data.get("visionInHead", ""),
        height=180,
        key="Trunk_vision",
        label_visibility="collapsed",
        placeholder=(
            "Describe what you see: the finished piece, the setting, the light, "
            "who will use it, how it feels to make it…"
        ),
    )

    if st.button("Save Trunk page", use_container_width=True):
        st.session_state.page_content["Trunk"]["materialsProcesses"] = materials
        st.session_state.page_content["Trunk"]["visionInHead"] = vision
        st.session_state.page_content["Trunk"]["agentComments"] = talis
        st.session_state.notes_history["Trunk"] = materials
        st.success("Saved.")

    if st.button("Move on to the Branches", use_container_width=True, key="trunk_to_branches"):
        st.session_state.page_content["Trunk"]["materialsProcesses"] = materials
        st.session_state.page_content["Trunk"]["visionInHead"] = vision
        st.session_state.page_content["Trunk"]["agentComments"] = talis
        st.session_state.notes_history["Trunk"] = materials
        st.session_state["pending_section"] = "Branches"
        st.rerun()


def _normalize_csv_header(header: str) -> str:
    return header.strip().lower().replace("_", " ")


def _pick_csv_column(fieldnames: list[str], candidates: list[str]) -> str | None:
    if not fieldnames:
        return None
    by_norm = {_normalize_csv_header(f): f for f in fieldnames if f}
    for candidate in candidates:
        if candidate in by_norm:
            return by_norm[candidate]
    for candidate in candidates:
        for norm, original in by_norm.items():
            if candidate in norm:
                return original
    return None


def _parse_number(value: str) -> float:
    if value is None:
        return 0.0
    cleaned = str(value).strip().replace(",", "").replace("$", "").replace("€", "")
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def format_sales_csv_to_fallen_leaves(raw: bytes) -> tuple[str | None, str | None]:
    """
    Parse Etsy, Shopify, or generic sales CSV into a numbered Fallen Leaves list.
    Returns (formatted_text, error_message).
    """
    text = raw.decode("utf-8-sig", errors="replace")
    if not text.strip():
        return None, "That file looks empty."

    try:
        sample = text[:4096]
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        return None, "Could not read column headers. Try exporting again as CSV."

    product_col = _pick_csv_column(
        reader.fieldnames,
        [
            "title",
            "item name",
            "listing title",
            "product title",
            "product",
            "lineitem name",
            "item",
            "name",
            "listing",
        ],
    )
    qty_col = _pick_csv_column(
        reader.fieldnames,
        [
            "quantity",
            "qty",
            "orders",
            "units sold",
            "number of sales",
            "sales",
            "lineitem quantity",
            "items sold",
        ],
    )
    revenue_col = _pick_csv_column(
        reader.fieldnames,
        [
            "net sales",
            "revenue",
            "order total",
            "total",
            "price",
            "amount",
            "lineitem price",
            "gross sales",
            "sales total",
        ],
    )

    if not product_col:
        return None, (
            "Could not find a product column. Look for Title, Product, or Item Name — "
            "or see Help for how to export from your shop."
        )

    totals: dict[str, dict[str, float]] = {}
    for row in reader:
        name = (row.get(product_col) or "").strip()
        if not name or name.lower() in {"total", "grand total", "subtotal"}:
            continue
        qty = _parse_number(row.get(qty_col, "")) if qty_col else 0.0
        rev = _parse_number(row.get(revenue_col, "")) if revenue_col else 0.0
        if qty_col is None and rev > 0:
            qty = 1.0
        bucket = totals.setdefault(name, {"qty": 0.0, "rev": 0.0})
        bucket["qty"] += qty
        bucket["rev"] += rev

    if not totals:
        return None, "No product rows found. Check that the file is a sales or orders export."

    sort_key = "qty" if qty_col else "rev"
    ranked = sorted(totals.items(), key=lambda item: item[1][sort_key], reverse=True)

    lines = [
        "Sorted from your shop file — highest to lowest:",
        "",
    ]
    for i, (name, stats) in enumerate(ranked, 1):
        parts = [name]
        if stats["qty"] > 0:
            qty_display = int(stats["qty"]) if stats["qty"] == int(stats["qty"]) else stats["qty"]
            parts.append(f"{qty_display} sold")
        if stats["rev"] > 0:
            parts.append(f"${stats['rev']:,.2f}")
        lines.append(f"{i}. {' — '.join(parts)}")

    return "\n".join(lines), None


def render_leaves_csv_help_expander() -> None:
    with st.expander("Need help exporting a shop file?"):
        st.markdown(
            """
**You do not have to build the list by hand.** Export a spreadsheet from your shop, upload it here,
and MakerTree sorts it into **Fallen Leaves** for you.

**Etsy:** Shop Manager → Settings → Options → Download Data → choose **Orders** or **Listings** → CSV.

**Shopify:** Orders or Products → Export → CSV.

**Any shop:** If the file has a **product name** column and **quantity** or **sales** columns, it should work.

For step-by-step pictures and tips, open **Help** from the main tree page.
            """
        )
        if st.button("Open Help page", key="leaves_open_help"):
            st.session_state["pending_section"] = "Help"
            st.rerun()


def render_help_page() -> None:
    """Guide makers through CSV exports — no spreadsheets expertise required."""
    st.subheader("Help — Shop files & uploads")
    st.caption(
        "Creatives often stall on files, taxes, and analytics. This page shows how to export once "
        "and let the tree do the sorting."
    )

    st.markdown("### Leaves — sales spreadsheets")
    st.markdown(
        """
On **Leaves**, use **Upload a sales spreadsheet** under Fallen Leaves. MakerTree reads Etsy, Shopify,
and most shop exports — then lists your products **highest to lowest**.

**What you need in the file:** a product or listing name, plus quantity sold and/or revenue.
You do **not** need to edit the spreadsheet first.
        """
    )

    st.markdown("#### Etsy")
    st.markdown(
        """
1. Open [Etsy Shop Manager](https://www.etsy.com/your/shops/me/tools).
2. Go to **Settings** → **Options** → **Download Data** (or Stats → Download).
3. Choose **Orders** or a sales report for the period you want.
4. Download the **CSV** file to your phone or computer.
5. On **Leaves**, tap **Upload a sales spreadsheet** and choose that file.
6. Tap **Sort into Fallen Leaves** — done.
        """
    )

    st.markdown("#### Shopify")
    st.markdown(
        """
1. In Shopify admin, open **Orders** or **Analytics** → **Reports**.
2. Export the report as **CSV** (orders with line items work best).
3. Upload on **Leaves** the same way as Etsy.
        """
    )

    st.markdown("#### Other shops & craft fairs")
    st.markdown(
        """
Square, WooCommerce, markets, or your own spreadsheet — if it has product names and sales counts,
upload it on **Leaves**. If something does not sort correctly, you can still edit the list by hand afterward.
        """
    )

    st.markdown("### Coming later on other branches")
    st.markdown(
        """
- **Soil** — inventory and year-end summaries  
- **Bark** — traffic and social analytics files  

Same idea: export once, upload, let Talis help you read it — not live API connections in the light app.
        """
    )

    if st.button("Go to Leaves to upload", use_container_width=True, key="help_to_leaves"):
        st.session_state["pending_section"] = "Leaves"
        st.rerun()


def _leaves_page_data() -> dict:
    data = st.session_state.page_content.setdefault("Leaves", {})
    if not data.get("fallenLeaves", "").strip():
        legacy = st.session_state.notes_history.get("Leaves", "")
        if legacy.strip():
            data["fallenLeaves"] = legacy
    data.setdefault("inactiveProducts", "")
    return data


def render_leaves_page() -> None:
    """Leaves — fallen sales/feedback and products still on the tree."""
    data = _leaves_page_data()
    st.subheader("Sales")
    st.caption("Products sold in order highest to lowest.")

    render_leaves_csv_help_expander()

    st.markdown("**Upload a sales spreadsheet (CSV)**")
    st.caption(
        "Export from Etsy, Shopify, or your shop — upload here instead of typing everything by hand."
    )
    uploaded = st.file_uploader(
        "Sales CSV",
        type=["csv"],
        key="leaves_csv_upload",
        label_visibility="collapsed",
    )
    if uploaded is not None:
        st.caption(f"File: {uploaded.name}")
        if st.button("Sort into Fallen Leaves", use_container_width=True, key="leaves_apply_csv"):
            formatted, err = format_sales_csv_to_fallen_leaves(uploaded.getvalue())
            if err:
                st.error(err)
            else:
                st.session_state.page_content["Leaves"]["fallenLeaves"] = formatted
                st.session_state.notes_history["Leaves"] = formatted
                st.success(f"Sorted {uploaded.name} into Fallen Leaves — highest to lowest.")
                st.rerun()

    st.markdown("**Fallen Leaves**")
    st.caption("Sales, Reviews, and Customer Feedback")
    fallen = st.text_area(
        "Fallen Leaves",
        value=data.get("fallenLeaves", ""),
        height=180,
        key="leaves_fallen",
        label_visibility="collapsed",
        placeholder="List products sold — highest to lowest — with sales, reviews, and customer feedback.",
    )

    st.markdown("**Leaves still on the tree**")
    st.caption("Inactive Products")
    inactive = st.text_area(
        "Inactive Products",
        value=data.get("inactiveProducts", ""),
        height=180,
        key="leaves_inactive",
        label_visibility="collapsed",
        placeholder="Products that haven't sold yet — still drying on the branch.",
    )

    st.markdown(f"**{TALIS_HELP_LABEL}**")
    st.caption(TALIS_HELP_CAPTION)
    chip_cols = st.columns(2)
    for i, chip in enumerate(talis_chips["Leaves"]):
        with chip_cols[i % 2]:
            if st.button(chip, key=f"chip_Leaves_{i}"):
                curr = data.get("fallenLeaves", "")
                new = curr + "\n\n" + chip if curr.strip() else chip
                st.session_state.page_content["Leaves"]["fallenLeaves"] = new
                st.rerun()

    if st.button("Save Leaves page", use_container_width=True):
        st.session_state.page_content["Leaves"]["fallenLeaves"] = fallen
        st.session_state.page_content["Leaves"]["inactiveProducts"] = inactive
        st.session_state.notes_history["Leaves"] = fallen
        st.success("Saved.")

    if st.button("Move to Soil", use_container_width=True, key="leaves_to_soil"):
        st.session_state.page_content["Leaves"]["fallenLeaves"] = fallen
        st.session_state.page_content["Leaves"]["inactiveProducts"] = inactive
        st.session_state.notes_history["Leaves"] = fallen
        if fallen.strip():
            soil_data = st.session_state.page_content.setdefault("Soil", {})
            from_leaves = f"**From Leaves (fallen — sales & feedback):**\n{fallen.strip()}"
            existing = soil_data.get("brainDump", "")
            if from_leaves not in existing:
                soil_data["brainDump"] = (
                    f"{existing}\n\n{from_leaves}".strip() if existing.strip() else from_leaves
                )
        st.session_state["pending_section"] = "Soil"
        st.rerun()


# Handle pending navigation from welcome page buttons (before main content renders)
if "pending_section" in st.session_state:
    st.session_state.current_section = st.session_state["pending_section"]
    del st.session_state["pending_section"]

# Clickable MakerTree logo header on every page (returns to main tree)
render_app_header()

# Mobile-first main content (stacks vertically on phones, tree photo anchors the main page)

# ============================================
# SYCAMORE GROVE ONBOARDING (first launch + return from Soil / Picnic)
# ============================================

if not st.session_state.grove_completed:
    render_sycamore_grove()
    st.stop()

# ============================================
# END SYCAMORE GROVE
# ============================================
section = st.session_state.current_section

if section == "Welcome":
    # Big central tree image on the main page
    if tree_image_path and os.path.exists(tree_image_path):
        st.image(tree_image_path, use_container_width=True)
        st.markdown("""
<div style="text-align: center; margin-top: 12px; margin-bottom: 24px;">
    <h3 style="margin-bottom: 4px;">Talis.</h3>
    <p style="margin-top: 0; font-size: 1.05rem;">A living Sycamore to help you design, create, and grow your creative business.</p>
</div>
""", unsafe_allow_html=True)
    else:
        st.warning("Central tree image not found. Expected at assets/images/central-tree.jpg inside the MakerTree folder.")
        st.image("https://via.placeholder.com/700x500/8B4513/FFFFFF?text=MakerTree", use_container_width=True)

    st.subheader("Where do you want to begin?")
    st.caption("Tap a branch below. Everything stays light and local.")

    # Tree navigation placed underneath the image (big tappable targets for mobile)
    # On desktop this will sit to the right of the flow naturally; on phone it stacks cleanly below.
    branches = [
        ("Rain", "🌧️  Rain — Brain dump everything"),
        ("Roots", "🌱  Roots — Ground & find your edge"),
        ("Trunk", "🪵  Trunk — Tools, materials, daily flow"),
        ("Branches", "🌿  Branches — Sales channels"),
        ("Bark", "📖  Bark — Storytelling & voice"),
        ("Leaves", "🍃  Leaves — Products & sales"),
        ("Soil", "🌍  Soil — Reviews, data, nourishment"),
        ("Picnic", "🧺  Picnic — Inner work & rest"),
        ("Help", "📎  Help — Shop files & uploads"),
    ]

    for key, label in branches:
        if st.button(label, key=f"nav_{key}", use_container_width=True):
            st.session_state["pending_section"] = key
            st.rerun()  # trigger rerun so early pending handler sets state before sidebar/content

else:
    # Subpage content — notes/context live here only (not on the main Welcome page)

    # Banner at top for all subpages — cropped like index.html (object-fit + object-position)
    render_section_banner(section)

    # Replicate structure from index.html project view for Rain, Roots, Bark, Soil:
    # (logo + banner already rendered above) + Brain Dump + Solutions & Processes + Agent + Current Project Notes
    # Rain has its own structure; Roots / Bark / Soil share the rich layout
    if section == "Rain":
        render_rain_page()

    elif section in ["Roots", "Bark", "Soil"]:
        data = st.session_state.page_content.get(section, {})
        st.subheader(data.get("firstHeader", section))

        if section == "Soil":
            st.markdown("Leaves are the sales")
            brain = st.text_area(
                "Leaves are the sales",
                value=data.get("brainDump", ""),
                height=260,
                key=f"{section}_brain",
                label_visibility="collapsed",
                placeholder="List your best selling items here.",
            )
        else:
            brain = st.text_area(
                "Brain Dump",
                value=data.get("brainDump", ""),
                height=260,
                key=f"{section}_brain",
                label_visibility="collapsed"
            )

        # Gemini Xprize call - specifically in Roots for competitive advantage + guardrails
        if section == "Roots":
            gemini_key = st.text_input(
                "Gemini API Key (paste from Google AI Studio - required for Xprize one-call compliance; $20 plan recommended)",
                type="password",
                key="gemini_key_roots"
            )
            if st.button("Parse Brain Dump with Gemini (Xprize-required call + guardrails)", use_container_width=True):
                if gemini_key and genai:
                    result = parse_with_gemini(brain, gemini_key)
                    st.success("Gemini response (copy key parts into Talis below):")
                    st.markdown(result)
                    # Auto-update agentComments with the result for persistence
                    st.session_state.page_content[section]["agentComments"] = result
                else:
                    st.error("Need valid Gemini API key. Get one at https://aistudio.google.com/app/apikey (or use the $20 plan for quota). Local stub below still works.")

        if section == "Bark":
            st.markdown("**New Channels to try**")
        elif section == "Soil":
            st.markdown("**Mold and disease**")
            st.markdown(
                "ideas that pile up and are not used can create mold. Be sure to utilize the rain "
                "for your creative output to be fed through the roots on your next flow through. "
                "Disease can happen from poor customer feedback, bad reviews, poor shipping, "
                "and sales channel conflict. List them all below."
            )
        else:
            st.markdown("**Solutions & Processes Worked Through**")
        solutions = st.text_area(
            "Solutions & Processes",
            value=data.get("solutions", ""),
            height=180,
            key=f"{section}_solutions",
            label_visibility="collapsed"
        )

        agent = data.get("agentComments", "")
        if section != "Bark":
            st.markdown("**Talis**")
            talis_area_kwargs = {
                "label": "Talis",
                "value": data.get("agentComments", ""),
                "height": 180,
                "key": f"{section}_agent",
                "label_visibility": "collapsed",
            }
            if section == "Soil":
                talis_area_kwargs["placeholder"] = (
                    "Talis may leave a brief note here — warm, practical, no pressure."
                )
            agent = st.text_area(**talis_area_kwargs)
            if section == "Soil":
                with st.expander("Inventory"):
                    st.markdown(
                        "**Which were your favorite products from this collection?**\n\n"
                        "**What items did you enjoy making most?**\n\n"
                        "**What was your least favorite item to work on?**  \n"
                        "Are you willing to put this item through the system again?"
                    )

        # Ways Talis can help — relevant to section
        if section in talis_chips:
            st.markdown(f"**{TALIS_HELP_LABEL}**")
            st.caption(TALIS_HELP_CAPTION)
            chip_cols = st.columns(4)
            for i, chip in enumerate(talis_chips[section]):
                with chip_cols[i % 4]:
                    if st.button(chip, key=f"chip_{section}_{i}"):
                        if section == "Bark":
                            curr = st.session_state.page_content[section].get("solutions", "")
                            new = curr + "\n\n" + chip if curr.strip() else chip
                            st.session_state.page_content[section]["solutions"] = new
                        else:
                            curr = st.session_state.page_content[section]["agentComments"]
                            new = curr + "\n\n" + chip if curr.strip() else chip
                            st.session_state.page_content[section]["agentComments"] = new
                        st.rerun()

            if section != "Soil":
                with st.expander("Talis Guide"):
                    if section == "Roots":
                        st.markdown("""
- If "I don't know what to make, I have too many ideas": "Tell me everything you love. How could you make these differently from what you've seen before?"
- If tired of a material: "What new material excites you even if it doesn't seem profitable?"
- For combinations: "How to combine without degrading each? Need new tools?"
- For many materials: "Keep separate or combine?"
- Always ask before leaving: "What do you see in your head?" Define each: material, tools, how displayed (lighting/color/atmosphere), who for, best setting.
See full in Talis.md
""")
                    elif section == "Bark":
                        st.markdown("""
If burned out on social: Suggest focus on 1-2 platforms. Offer help with copy, stories, hashtags, workflows.
- Instagram: new + visual story
- Pinterest: products + URLs/inspiration
- Facebook: maker life + benefits
- Tumblr: image + process (no shop links)
- TikTok: live + process + humor
- Substack: feeling behind product
- X: how products improve the world
See full in Talis.md
""")
                    else:
                        st.markdown("See full guardrails and templates in MakerTree/notes/Talis.md for this section.")

        st.divider()
        st.markdown("**Current Project Notes**")
        current_notes = st.text_area(
            "Current Project Notes",
            value=st.session_state.notes_history.get(section, ""),
            height=160,
            key=f"{section}_notes",
            label_visibility="collapsed"
        )

        if st.button(f"Save {section} page", use_container_width=True):
            st.session_state.page_content[section]["brainDump"] = brain
            st.session_state.page_content[section]["solutions"] = solutions
            if section != "Bark":
                st.session_state.page_content[section]["agentComments"] = agent
            st.session_state.notes_history[section] = current_notes
            st.success("Saved. Structure matches the rich version (banner + three main areas + notes).")

        if section == "Bark":
            if st.button("Move on to the Leaves", use_container_width=True, key="bark_to_leaves"):
                st.session_state.page_content[section]["brainDump"] = brain
                st.session_state.page_content[section]["solutions"] = solutions
                st.session_state.notes_history[section] = current_notes
                st.session_state["pending_section"] = "Leaves"
                st.rerun()

        if section == "Soil":
            render_return_to_grove_button("Soil")

    elif section == "Trunk":
        render_trunk_page()

    elif section == "Branches":
        st.subheader("Sales Channels")
        st.markdown("**Active branches**")
        st.text_area(
            "Active branches",
            height=180,
            key="branches_active",
            label_visibility="collapsed",
        )
        st.caption("List where you are selling now.")

        # Chips for Branches
        if "Branches" in talis_chips:
            st.markdown(f"**{TALIS_HELP_LABEL}**")
            st.caption(TALIS_HELP_CAPTION)
            chip_cols = st.columns(4)
            for i, chip in enumerate(talis_chips["Branches"]):
                with chip_cols[i % 4]:
                    if st.button(chip, key=f"chip_Branches_{i}"):
                        curr = st.session_state.notes_history.get("Branches", "")
                        new = curr + "\n\n" + chip if curr.strip() else chip
                        st.session_state.notes_history["Branches"] = new
                        st.rerun()

        st.divider()
        st.subheader("Your notes for Branches")
        branches_note = st.text_area(
            "Add anything you want to remember or carry forward",
            st.session_state.notes_history.get("Branches", ""),
            height=200,
            key="note_Branches"
        )
        if st.button("Save notes for Branches"):
            st.session_state.notes_history["Branches"] = branches_note
            st.success("Saved.")

        if st.button("Move on to the Bark", use_container_width=True, key="branches_to_bark"):
            st.session_state.notes_history["Branches"] = branches_note
            st.session_state["pending_section"] = "Bark"
            st.rerun()

    elif section == "Leaves":
        render_leaves_page()

    elif section == "Help":
        render_help_page()

    elif section == "Picnic":
        st.write("Quilt on the grass — peaceful inner work. Fears, joy, imposter feelings, rest, character growth.")
        st.text_area("Sit here a while", "What feels heavy or wonderful today?", height=200, key="picnic_sit")

        # Chips for Picnic
        if "Picnic" in talis_chips:
            st.markdown(f"**{TALIS_HELP_LABEL}**")
            st.caption(TALIS_HELP_CAPTION)
            chip_cols = st.columns(4)
            for i, chip in enumerate(talis_chips["Picnic"]):
                with chip_cols[i % 4]:
                    if st.button(chip, key=f"chip_Picnic_{i}"):
                        curr = st.session_state.notes_history.get("Picnic", "")
                        new = curr + "\n\n" + chip if curr.strip() else chip
                        st.session_state.notes_history["Picnic"] = new
                        st.rerun()

        st.divider()
        st.subheader("Your notes for Picnic")
        picnic_note = st.text_area(
            "Add anything you want to remember or carry forward",
            st.session_state.notes_history.get("Picnic", ""),
            height=200,
            key="note_Picnic"
        )
        if st.button("Save notes for Picnic"):
            st.session_state.notes_history["Picnic"] = picnic_note
            st.success("Saved.")

        render_return_to_grove_button("Picnic")

    render_back_to_tree_button(section)
