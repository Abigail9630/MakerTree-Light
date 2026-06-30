import streamlit as st
import os
import base64
import csv
import io
import re
from datetime import datetime
from pathlib import Path

# Gemini: X Prize compliance only — env/secrets, not shown to makers (see run_gemini_hackathon_compliance)
try:
    import google.generativeai as genai
except ImportError:
    genai = None

from talis_gemma import gemma_setup_hint
from talis_ask_ui import (
    flush_pending_talis_widget,
    render_app_settings,
    render_manual_badge,
    render_talis_chips,
    run_ask_talis,
)
from talis_service import init_talis_prefs, process_pending_chip_assist
from maker_tree_library_ui import get_store, render_library_page, render_quick_capture_bar

st.set_page_config(page_title="MakerTree Beta", layout="wide", initial_sidebar_state="collapsed")

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

/* Focus ring — green (not error-red) on all text fields */
.stTextArea textarea,
.stTextInput input,
.stNumberInput input,
textarea,
input[type="text"],
input[type="search"],
input[type="password"] {
    outline-color: #166534 !important;
}
.stTextArea textarea:focus,
.stTextArea textarea:focus-visible,
.stTextInput input:focus,
.stTextInput input:focus-visible,
.stNumberInput input:focus,
.stNumberInput input:focus-visible,
textarea:focus,
textarea:focus-visible,
input[type="text"]:focus,
input[type="text"]:focus-visible,
input[type="search"]:focus,
input[type="search"]:focus-visible,
input[type="password"]:focus,
input[type="password"]:focus-visible {
    outline: 2px solid #166534 !important;
    outline-offset: 1px !important;
    border-color: #166534 !important;
    box-shadow: 0 0 0 1px rgba(22, 101, 52, 0.45) !important;
}
div[data-baseweb="select"]:focus-within,
div[data-baseweb="textarea"]:focus-within,
div[data-baseweb="input"]:focus-within {
    border-color: #166534 !important;
    box-shadow: 0 0 0 1px rgba(22, 101, 52, 0.45) !important;
}

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

@media (max-width: 640px) {
    html, body, [class*="css"], .stMarkdown, .stTextArea, .stButton>button {
        font-size: 17px !important;
    }
    .stButton>button {
        min-height: 48px !important;
        padding: 0.6rem 1rem !important;
    }
    .tree-progress-caption {
        font-size: 0.85rem !important;
        line-height: 1.5 !important;
    }
}

/* Tree progress bar — deep gold (dark goldenrod) + thin edge for dark screens */
div[data-testid="stProgressBar"] > div > div {
    background-color: rgba(184, 134, 11, 0.22) !important;
    border-radius: 6px !important;
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
    box-sizing: border-box !important;
}
div[data-testid="stProgressBar"] > div > div > div {
    background-color: #B8860B !important;
    border-radius: 5px !important;
}
.stProgress > div > div > div > div {
    background-color: #B8860B !important;
}
.stProgress > div > div > div {
    background-color: rgba(184, 134, 11, 0.22) !important;
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
    border-radius: 6px !important;
    box-sizing: border-box !important;
}

.tree-progress-caption {
    margin: 0.35rem 0 0.75rem 0 !important;
    letter-spacing: 0.01em;
}
.tree-progress-current {
    font-weight: 700 !important;
    font-size: 1.05em !important;
}
.tree-progress-step {
    font-weight: 500 !important;
    font-size: 0.82em !important;
    opacity: 0.72;
}
.tree-progress-arrow {
    font-size: 0.78em !important;
    opacity: 0.55;
    padding: 0 0.15em;
}
.manual-mode-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    background: #4a5568;
    color: #f3f4f6;
    font-size: 0.82rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    margin-top: 0.35rem;
}
@media (prefers-color-scheme: dark) {
    .manual-mode-badge {
        background: #64748b;
        color: #fff;
    }
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

# Main maker journey (Picnic and Help are side paths off the tree)
TREE_FLOW = ["Rain", "Roots", "Trunk", "Branches", "Bark", "Leaves", "Soil"]


def go_to_section(section: str) -> None:
    st.session_state["pending_section"] = section
    st.rerun()


def get_gemini_api_key() -> str:
    """Optional cloud key — env var, Streamlit secrets, or session paste."""
    if "gemini_api_key" not in st.session_state:
        env_key = os.environ.get("GEMINI_API_KEY", "")
        try:
            secrets_key = st.secrets.get("GEMINI_API_KEY", "")
        except (FileNotFoundError, KeyError, AttributeError):
            secrets_key = ""
        st.session_state.gemini_api_key = env_key or secrets_key or ""
    return st.session_state.gemini_api_key


def get_llama_cpp_host() -> str:
    """llama.cpp server URL — session override, secrets, env, or default."""
    if st.session_state.get("llama_cpp_host", "").strip():
        return st.session_state.llama_cpp_host.strip().rstrip("/")
    try:
        secrets_host = st.secrets.get("LLAMA_CPP_HOST", "")
    except (FileNotFoundError, KeyError, AttributeError):
        secrets_host = ""
    return (
        secrets_host
        or os.environ.get("LLAMA_CPP_HOST")
        or "http://127.0.0.1:8080"
    ).rstrip("/")


def render_tree_progress(section: str) -> None:
    """Show where the maker is in the Rain → Soil cycle."""
    if section not in TREE_FLOW:
        return
    idx = TREE_FLOW.index(section)
    st.progress((idx + 1) / len(TREE_FLOW))
    parts = []
    for i, name in enumerate(TREE_FLOW):
        if i == idx:
            parts.append(f'<span class="tree-progress-current">{name}</span>')
        else:
            parts.append(f'<span class="tree-progress-step">{name}</span>')
    trail = ' <span class="tree-progress-arrow">→</span> '.join(parts)
    st.markdown(f'<p class="tree-progress-caption">{trail}</p>', unsafe_allow_html=True)


def render_flow_step_nav(section: str) -> None:
    """Compact previous / next step links along the main tree path."""
    if section not in TREE_FLOW:
        return
    idx = TREE_FLOW.index(section)
    prev_section = TREE_FLOW[idx - 1] if idx > 0 else None
    next_section = TREE_FLOW[idx + 1] if idx < len(TREE_FLOW) - 1 else None
    if not prev_section and not next_section:
        return
    col_prev, col_next = st.columns(2)
    with col_prev:
        if prev_section:
            if st.button(
                f"← Back: {prev_section}",
                key=f"flow_prev_{section}",
                use_container_width=True,
            ):
                go_to_section(prev_section)
    with col_next:
        if next_section:
            if st.button(
                f"Next: {next_section} →",
                key=f"flow_next_{section}",
                use_container_width=True,
            ):
                go_to_section(next_section)


def run_gemini_hackathon_compliance() -> None:
    """One Gemini API call for X Prize rules — env/secrets only, invisible to makers."""
    if st.session_state.get("gemini_hackathon_done"):
        return
    api_key = get_gemini_api_key()
    if not api_key or genai is None:
        return
    try:
        parse_with_gemini(
            "Welcome to MakerTree — a maker planted roots in the Sycamore Grove.",
            api_key,
            "Grove",
        )
        st.session_state.gemini_hackathon_done = True
    except Exception:
        pass


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

    logo_col, title_col, status_col = st.columns([0.09, 0.35, 0.56], vertical_alignment="center")
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
            help="Back to the main tree — MakerTree Beta",
        ):
            go_home = True
    with status_col:
        render_manual_badge()

    if go_home:
        st.session_state["pending_section"] = "Welcome"
        st.rerun()


def complete_grove() -> None:
    """Mark Grove onboarding done and continue to the tree."""
    grove_flag.touch()
    st.session_state.grove_completed = True
    st.session_state.return_to_grove = False
    st.session_state.grove_form_stage = 1
    run_gemini_hackathon_compliance()


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
    try:
        rel_path, object_pos = SECTION_BANNERS.get(section, (None, "center 20%"))
        if rel_path:
            banner_file = os.path.join(script_dir, rel_path)
        else:
            banner_file = tree_image_path
            object_pos = "center 20%"

        if not banner_file or not os.path.exists(banner_file):
            st.caption("Banner image loading — you can keep working below.")
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
    except OSError:
        st.caption("Banner image unavailable — continuing without it.")
    except Exception:
        st.caption("Something went wrong loading the banner — you can keep working below.")


def parse_with_gemini(content: str, api_key: str, section: str = "Roots") -> str:
    """Call Gemini for section-aware parsing — optional cloud assist."""
    if genai is None:
        return "Install google-generativeai first: pip install google-generativeai"
    if not api_key:
        return "Please provide a Gemini API key (from Google AI Studio)."
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')  # fast and sufficient for this
        prompt = f"""You are a gentle, wise maker mentor helping turn notes into clear next steps. Stay warm, first-person, practical (no "we/our", no "magic").

Section: {section}

Parse and organize this content for the maker. Keep responses concise and actionable.

Content:
{content}"""
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
                "When sorting your ideas, I'll separate your vision towards Roots and daily life toward Picnic. "
                "I'll be your guide and help point you toward more efficient and beautiful products."
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
        "Picnic": {
            "journal": "",
            "journalDate": "",
            "stallType": "",
            "talisNotes": "",
            "makerCategory": "",
            "profileTools": "",
        },
        "Roots": {
            "firstHeader": "Raw Ideas",
            "brainDump": "Roots\n\nWhere the real grounding happens. This is where the agent steps in to help parse the rain into clear, usable ideas. We sort, research, identify competitive advantage, decide on materials, price points, and processes. The roots keep the whole tree stable. You can click directly here if you've already dumped in the rain.",
            "solutions": "",
            "agentComments": "",
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
        "What feels heavy or wonderful right now?",
        "What part of this process is closest to what you see in your head?",
        "One small thing that would feel like rest",
        "No thanks — just let me write",
    ],
}

# Sycamore Grove maker categories (Define-MakerTree.md) — seeds Gemma / Picnic niche packs
GROVE_CATEGORIES = [
    "Paper & Binding",
    "Fiber & Textiles",
    "Leather & Stitch",
    "Wood & Carving",
    "Clay & Ceramics",
    "Mark Making",
    "Metal & Forge",
    "Homestead Craft",
]

PICNIC_STALL_TYPES = {
    "imposter": "Imposter syndrome — not sure I'm a real maker",
    "skill_gap": "Missing a skill to finish what I started",
    "over_excited": "Over-excited about one idea — can't settle",
    "fear": "Afraid — pricing, visibility, or judgment",
    "rest": "Just need rest (not stuck, just tired)",
    "other": "Something else — I'll write it",
}

# Extra chips per craft — merged with base Picnic chips in the UI
NICHE_PICNIC_CHIPS: dict[str, list[str]] = {
    "Fiber & Textiles": [
        "Everyone else seems more skilled at finishing",
        "This fabric / stitch is harder than I thought",
        "I'm excited about every colorway at once",
    ],
    "Wood & Carving": [
        "Afraid to ruin expensive stock on the lathe",
        "My work doesn't look 'professional' enough",
        "I bought a new tool and haven't touched it",
    ],
    "Clay & Ceramics": [
        "Kiln results never match what I pictured",
        "Comparing my pots to Instagram makers",
        "One glaze idea has taken over everything else",
    ],
    "Metal & Forge": [
        "Scared of the heat / equipment",
        "Who am I to call myself a smith?",
        "One blade design won't leave my head",
    ],
    "Homestead Craft": [
        "Labeling / legal stuff feels overwhelming",
        "My kitchen experiments aren't 'real' products",
        "Too many jar flavors to pick one",
    ],
}

# Where Talis may gently send the maker after Picnic (not mandatory workflow steps)
PICNIC_RETURN_HINTS: dict[str, list[tuple[str, str]]] = {
    "imposter": [
        ("Roots", "Ground the idea — what's actually yours?"),
        ("Trunk", "Small proof make — one piece, no audience"),
        ("Rain", "Pour it out again — no sorting yet"),
    ],
    "skill_gap": [
        ("Trunk", "Tools & steps — break the skill into one lesson"),
        ("Help", "Find a class, book, or mentor"),
        ("Roots", "Clarify what 'done' looks like"),
    ],
    "over_excited": [
        ("Roots", "Pick one product to carry forward"),
        ("Rain", "Brain dump everything — Talis sorts later"),
        ("Trunk", "Reality-check materials and time"),
    ],
    "fear": [
        ("Bark", "One small post — process, not perfection"),
        ("Branches", "Smallest sales step (one channel)"),
        ("Picnic", "Stay here longer"),
    ],
    "rest": [
        ("Welcome", "Back to the tree when ready"),
    ],
    "other": [
        ("Rain", "Brain dump"),
        ("Welcome", "Choose another branch"),
    ],
}

# Preview responses until Gemma is wired (category + stall → warm Talis voice)
PICNIC_TALIS_PREVIEW: dict[tuple[str, str], str] = {
    (
        "Fiber & Textiles",
        "imposter",
    ): (
        "Seamstresses and upcyclers often feel like 'real' makers only if the inside finish is perfect. "
        "Your edge may be the story in the fabric, not factory polish. One small finished piece counts."
    ),
    (
        "Wood & Carving",
        "skill_gap",
    ): (
        "On the lathe, the gap is usually one setup — speed, gouge, or grain direction — not your talent. "
        "Trunk is the place for one practice blank before the piece you care about."
    ),
    (
        "Clay & Ceramics",
        "over_excited",
    ): (
        "When every glaze idea fires at once, pick one test tile this week. The rest can wait in Rain "
        "without dying — you are not losing them."
    ),
    (
        "Metal & Forge",
        "fear",
    ): (
        "Visibility fear is common at the anvil — the work feels personal because it is. "
        "Bark can hold a 10-second spark clip with no shop link; nothing has to go on sale yet."
    ),
}


def _picnic_page_data() -> dict:
    data = st.session_state.page_content.setdefault("Picnic", {})
    if not data.get("journal", "").strip():
        legacy = st.session_state.notes_history.get("Picnic", "")
        if legacy.strip():
            data["journal"] = legacy
    data.setdefault("journalDate", "")
    data.setdefault("stallType", "")
    data.setdefault("talisNotes", "")
    data.setdefault("makerCategory", "")
    return data


def _picnic_chips_for_category(category: str) -> list[str]:
    base = list(talis_chips["Picnic"])
    extra = NICHE_PICNIC_CHIPS.get(category, [])
    return base + extra


def talis_picnic_preview_response(category: str, stall_key: str, journal: str) -> str:
    """Static niche preview until Gemma runs locally."""
    key = (category, stall_key)
    if key in PICNIC_TALIS_PREVIEW:
        body = PICNIC_TALIS_PREVIEW[key]
    elif stall_key == "rest":
        body = "Rest is part of the cycle — not a detour. You do not have to produce anything to belong here."
    elif stall_key == "imposter":
        body = (
            "Imposter feelings mean you care about the work — not that you are faking. "
            "Many makers stall here before Trunk, not because the idea is wrong."
        )
    elif stall_key == "skill_gap":
        body = (
            "A missing skill is a Trunk problem, not a character flaw. "
            "One tutorial, one practice piece, or one human who has done it before."
        )
    elif stall_key == "over_excited":
        body = (
            "Excitement is rain energy — beautiful and messy. Roots can hold one thread "
            "while the rest waits without shame."
        )
    elif stall_key == "fear":
        body = (
            "Fear of being seen is common when the work feels personal. "
            "You can take a smaller step in Bark without committing to the whole shop."
        )
    else:
        body = (
            "I am here with you on the quilt. Write what is true; when you are ready, "
            "the tree still has a branch that fits."
        )
    if journal.strip():
        body += f"\n\nYou wrote: “{journal.strip()[:200]}{'…' if len(journal.strip()) > 200 else ''}” — I hear you."
    return body


def render_picnic_page() -> None:
    """Picnic — side path for inner work; not an end point in the tree cycle."""
    data = _picnic_page_data()
    st.subheader("Picnic on the quilt")
    st.caption(
        "Side path — not a step in the Rain → Soil cycle. Sit as long as you need. "
        "Stalls here (imposter feelings, skill gaps, over-excitement, fear) get named so "
        "you can re-enter the tree when ready — not because you failed."
    )
    st.markdown(
        "*Talis is a gentle companion, not a therapist. For anything heavy, reach a real person you trust.*"
    )

    with st.expander("Your maker profile (for Talis — from Grove or pick here)"):
        st.caption(
            "Gemma uses this to tailor Picnic advice — seamstress vs woodturner vs potter. "
            "Update anytime; Grove form will fill this automatically later."
        )
        category = st.selectbox(
            "Primary craft",
            [""] + GROVE_CATEGORIES,
            index=(
                (GROVE_CATEGORIES.index(data["makerCategory"]) + 1)
                if data.get("makerCategory") in GROVE_CATEGORIES
                else 0
            ),
            key="picnic_maker_category",
            placeholder="Choose your grove category…",
        )
        if category:
            data["makerCategory"] = category
        profile_tools = st.text_input(
            "Main tools (short)",
            value=data.get("profileTools", ""),
            key="picnic_profile_tools",
            placeholder="e.g. serger, dress form / lathe, gouges",
        )
        data["profileTools"] = profile_tools

    st.markdown("**Journal this Workflow**")
    stored_date = data.get("journalDate", "")
    if stored_date:
        try:
            default_journal_date = datetime.strptime(stored_date, "%Y-%m-%d").date()
        except ValueError:
            default_journal_date = datetime.now().date()
    else:
        default_journal_date = datetime.now().date()
    journal_date = st.date_input(
        "Date",
        value=default_journal_date,
        key="picnic_journal_date",
        format="MM/DD/YYYY",
    )
    journal = st.text_area(
        "Picnic journal",
        value=data.get("journal", ""),
        height=200,
        key="picnic_journal",
        label_visibility="collapsed",
        placeholder=(
            "Express how you're feeling about your projects right now. "
            "Imposter thoughts, a skill you lack, one idea taking over — no pressure."
        ),
    )

    st.markdown("**What kind of stall is this?** *(helps Talis tailor — optional)*")
    stall_options = [""] + list(PICNIC_STALL_TYPES.keys())
    stall_labels = ["Choose if it fits…"] + list(PICNIC_STALL_TYPES.values())
    stall_index = (
        stall_options.index(data["stallType"])
        if data.get("stallType") in stall_options
        else 0
    )
    stall_choice = st.selectbox(
        "Stall type",
        options=range(len(stall_options)),
        format_func=lambda i: stall_labels[i],
        index=stall_index,
        key="picnic_stall_select",
        label_visibility="collapsed",
    )
    stall_key = stall_options[stall_choice] if stall_choice > 0 else ""

    category = data.get("makerCategory", "")
    chips = _picnic_chips_for_category(category) if category else talis_chips["Picnic"]

    render_talis_chips(
        "Picnic",
        chips,
        {"journal": journal, "stallType": stall_key, "category": category},
        num_cols=2,
    )

    st.markdown("**Talis**")
    talis_default = flush_pending_talis_widget(
        "picnic_talis", data.get("talisNotes", "")
    )
    talis_notes = st.text_area(
        "Talis",
        value=talis_default,
        height=140,
        key="picnic_talis",
        label_visibility="collapsed",
        placeholder="Talis may reflect here — warm, brief, no pressure.",
    )

    llama_host = get_llama_cpp_host()
    stall_label = PICNIC_STALL_TYPES.get(stall_key, stall_key or "unspecified")

    def _save_picnic_talis(text: str) -> None:
        data["talisNotes"] = text
        data["journal"] = journal
        data["journalDate"] = journal_date.isoformat()
        data["stallType"] = stall_key
        st.session_state.notes_history["Picnic"] = journal

    run_ask_talis(
        "Picnic",
        llama_host=llama_host,
        snapshot={
            "journal": journal,
            "stall_label": stall_label,
            "category": category,
            "maker_profile": {
                "tools": data.get("profileTools", ""),
                "materials": "",
                "experience": "",
            },
        },
        widget_key="picnic_talis",
        save_to_page=_save_picnic_talis,
        fallback=lambda: talis_picnic_preview_response(category, stall_key, journal),
    )

    with st.expander("How Talis personalizes for your craft"):
        st.markdown(
            """
**Your Grove profile** — craft category and tools from Sycamore Grove (or pick above).

**Stall type** — imposter, skill gap, over-excitement, fear, or rest shapes how Talis responds.

**Niche packs** — craft-specific suggestions (fiber, wood, clay, metal, and more).

**Gemma 2B on your machine** — local Talis via llama.cpp; **no API key**. Guardrails in `Talis.md`.
            """
        )

    st.divider()
    st.markdown("**When you're ready — where next?**")
    st.caption("Suggestions only. Picnic is not an exit — pick a branch or return to the tree.")
    hints = PICNIC_RETURN_HINTS.get(stall_key or "other", PICNIC_RETURN_HINTS["other"])
    hint_cols = st.columns(min(len(hints), 3))
    for i, (branch, hint) in enumerate(hints):
        with hint_cols[i % len(hint_cols)]:
            if st.button(f"{branch}", key=f"picnic_go_{branch}_{i}", use_container_width=True):
                data["journal"] = journal
                data["journalDate"] = journal_date.isoformat()
                data["talisNotes"] = talis_notes
                data["stallType"] = stall_key
                st.session_state.notes_history["Picnic"] = journal
                if branch == "Picnic":
                    st.rerun()
                else:
                    go_to_section(branch if branch != "Welcome" else "Welcome")

    if st.button("Save Picnic", use_container_width=True, key="picnic_save"):
        data["journal"] = journal
        data["journalDate"] = journal_date.isoformat()
        data["talisNotes"] = talis_notes
        data["stallType"] = stall_key
        st.session_state.notes_history["Picnic"] = journal
        st.success("Saved. Take your time — the tree will be here.")

    render_return_to_grove_button("Picnic")


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

    st.markdown("**Talis**")
    talis = st.text_area(
        "Talis",
        value=data.get("agentComments", ""),
        height=120,
        key="Rain_talis",
        label_visibility="collapsed",
        placeholder="When sorting your ideas, I'll separate your vision towards Roots and daily life toward Picnic…",
    )

    render_talis_chips(
        "Rain",
        talis_chips["Rain"],
        {"brainDump": brain, "talisProjectNotes": data.get("talisProjectNotes", "")},
        num_cols=3,
    )

    st.divider()
    st.markdown("**Talis Project Notes**")
    st.caption(
        "Talis recommends groupings here — **Roots** vs **Picnic**. You move items yourself."
    )
    talis_notes_default = flush_pending_talis_widget(
        "Rain_talis_project_notes",
        data.get("talisProjectNotes", RAIN_TALIS_PROJECT_NOTES_STARTER),
    )
    talis_project_notes = st.text_area(
        "Talis Project Notes",
        value=talis_notes_default,
        height=220,
        key="Rain_talis_project_notes",
        label_visibility="collapsed",
    )

    llama_host = get_llama_cpp_host()
    run_ask_talis(
        "Rain",
        llama_host=llama_host,
        snapshot={"brainDump": brain, "talisProjectNotes": talis_project_notes},
        widget_key="Rain_talis_project_notes",
        save_to_page=lambda t: st.session_state.page_content["Rain"].update(
            {"talisProjectNotes": t}
        ),
        fallback=lambda: (
            "I can suggest groupings for Roots and Picnic — try a chip or Ask Talis."
        ),
    )

    st.markdown("**Corrections for Talis**")
    st.caption(
        "If something landed in the wrong place, or you want Talis to sort differently, say so here."
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


def render_roots_page() -> None:
    """Roots — brain dump, Talis chips, then solutions & project notes at the bottom."""
    data = st.session_state.page_content.get("Roots", {})
    st.subheader(data.get("firstHeader", "Roots"))

    brain = st.text_area(
        "Brain Dump",
        value=data.get("brainDump", ""),
        height=260,
        key="Roots_brain",
        label_visibility="collapsed",
    )

    render_talis_chips(
        "Roots",
        talis_chips["Roots"],
        {"brainDump": brain, "solutions": data.get("solutions", "")},
        num_cols=4,
    )

    with st.expander("Talis Guide"):
        st.markdown("""
- If "I don't know what to make, I have too many ideas": "Tell me everything you love. How could you make these differently from what you've seen before?"
- If tired of a material: "What new material excites you even if it doesn't seem profitable?"
- For combinations: "How to combine without degrading each? Need new tools?"
- For many materials: "Keep separate or combine?"
- Always ask before leaving: "What do you see in your head?" Define each: material, tools, how displayed (lighting/color/atmosphere), who for, best setting.

See full in Talis.md
""")

    llama_host = get_llama_cpp_host()
    solutions_val = data.get("solutions", "")

    st.markdown("**Talis**")
    agent_default = flush_pending_talis_widget("Roots_agent", data.get("agentComments", ""))
    agent = st.text_area(
        "Talis",
        value=agent_default,
        height=180,
        key="Roots_agent",
        label_visibility="collapsed",
        placeholder="Talis may leave a note here — practical, grounded, no pressure.",
    )

    run_ask_talis(
        "Roots",
        llama_host=llama_host,
        snapshot={"brainDump": brain, "solutions": solutions_val, "agentComments": agent},
        widget_key="Roots_agent",
        save_to_page=lambda t: st.session_state.page_content["Roots"].update({"agentComments": t}),
        fallback=lambda: (
            "I read your rain and roots together — grouped by material, process, and tool when I can."
        ),
    )

    st.divider()
    st.markdown("**Solutions & Processes Worked Through**")
    solutions = st.text_area(
        "Solutions & Processes",
        value=data.get("solutions", ""),
        height=180,
        key="Roots_solutions",
        label_visibility="collapsed",
    )

    st.markdown("**Current Project Notes**")
    current_notes = st.text_area(
        "Current Project Notes",
        value=st.session_state.notes_history.get("Roots", ""),
        height=160,
        key="Roots_notes",
        label_visibility="collapsed",
    )

    if st.button("Save Roots page", use_container_width=True):
        st.session_state.page_content["Roots"]["brainDump"] = brain
        st.session_state.page_content["Roots"]["solutions"] = solutions
        st.session_state.page_content["Roots"]["agentComments"] = agent
        st.session_state.notes_history["Roots"] = current_notes
        st.success("Saved.")


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
    talis_default = flush_pending_talis_widget(
        "Trunk_talis", data.get("agentComments", "")
    )
    talis = st.text_area(
        "Talis",
        value=talis_default,
        height=120,
        key="Trunk_talis",
        label_visibility="collapsed",
        placeholder="Talis may leave a brief note here — practical, grounded, no pressure.",
    )

    if "Trunk" in talis_chips:
        render_talis_chips(
            "Trunk",
            talis_chips["Trunk"],
            {"materialsProcesses": materials, "visionInHead": data.get("visionInHead", "")},
            num_cols=2,
        )

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

    llama_host = get_llama_cpp_host()

    def _save_trunk_talis(text: str) -> None:
        st.session_state.page_content["Trunk"]["agentComments"] = text

    run_ask_talis(
        "Trunk",
        llama_host=llama_host,
        snapshot={"materialsProcesses": materials, "visionInHead": vision},
        widget_key="Trunk_talis",
        save_to_page=_save_trunk_talis,
        fallback=lambda: (
            "I am looking at your materials and the picture in your head. "
            "One clear next step in the shop beats a perfect plan."
        ),
    )

    if st.button("Save Trunk page", use_container_width=True):
        st.session_state.page_content["Trunk"]["materialsProcesses"] = materials
        st.session_state.page_content["Trunk"]["visionInHead"] = vision
        st.session_state.page_content["Trunk"]["agentComments"] = talis
        st.session_state.notes_history["Trunk"] = materials
        st.success("Saved.")


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

Same idea: export once, upload, let Talis help you read it — not live API connections in MakerTree Beta.
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
            try:
                formatted, err = format_sales_csv_to_fallen_leaves(uploaded.getvalue())
                if err:
                    st.error(err)
                else:
                    st.session_state.page_content["Leaves"]["fallenLeaves"] = formatted
                    st.session_state.notes_history["Leaves"] = formatted
                    st.success(f"Sorted {uploaded.name} into Fallen Leaves — highest to lowest.")
                    st.rerun()
            except Exception:
                st.error("Could not read that file. Try exporting again as CSV from your shop.")

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

    render_talis_chips(
        "Leaves",
        talis_chips["Leaves"],
        {"fallenLeaves": fallen, "inactiveProducts": inactive},
        num_cols=2,
    )
    llama_host = get_llama_cpp_host()
    run_ask_talis(
        "Leaves",
        llama_host=llama_host,
        snapshot={"fallenLeaves": fallen, "inactiveProducts": inactive},
        widget_key="leaves_fallen",
        save_to_page=lambda t: st.session_state.page_content["Leaves"].update({"fallenLeaves": t}),
        fallback=lambda: "Review what sold and what is still on the branch — one item at a time.",
    )

    if st.button("Save Leaves page", use_container_width=True):
        st.session_state.page_content["Leaves"]["fallenLeaves"] = fallen
        st.session_state.page_content["Leaves"]["inactiveProducts"] = inactive
        st.session_state.notes_history["Leaves"] = fallen
        st.success("Saved.")


# Handle pending navigation from welcome page buttons (before main content renders)
if "pending_section" in st.session_state:
    st.session_state.current_section = st.session_state["pending_section"]
    del st.session_state["pending_section"]

# Clickable MakerTree logo header on every page (returns to main tree)
render_app_header()
render_app_settings(get_llama_cpp_host)

# Quick Capture on every page except Library (full bar lives there)
if st.session_state.get("grove_completed") and st.session_state.current_section != "Library":
    render_quick_capture_bar(get_store(), compact=True)

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
init_talis_prefs()
if process_pending_chip_assist(get_llama_cpp_host()):
    pass

section = st.session_state.current_section

if section == "Welcome":
    # Big central tree image on the main page
    if tree_image_path and os.path.exists(tree_image_path):
        st.image(tree_image_path, use_container_width=True)
        st.markdown("""
<div style="text-align: center; margin-top: 12px; margin-bottom: 24px;">
    <h3 style="margin-bottom: 4px;">Talis.</h3>
    <p style="margin-top: 0; font-size: 1.05rem;">MakerTree Beta — a living Sycamore to help you design, create, and grow your creative business.</p>
</div>
""", unsafe_allow_html=True)
    else:
        st.warning("Central tree image not found. Expected at assets/images/central-tree.jpg inside the MakerTree folder.")
        st.image("https://via.placeholder.com/700x500/8B4513/FFFFFF?text=MakerTree", use_container_width=True)

    st.subheader("Where do you want to begin?")
    st.caption("Tap a branch below. Local-first — your tree, your machine.")

    with st.expander("How Talis works (short version)"):
        st.markdown(
            """
**Talis (local Gemma)** runs on your machine — no cloud account needed for daily use.

Your **Sycamore Grove** profile and your words on each page shape her replies. Tap **Ways Talis can help** chips or **Ask Talis** when your local server is running (llama.cpp, port 8086).

Turn Talis off anytime in **Settings** for fully manual mode.
            """
        )

    # Tree navigation placed underneath the image
    branches = [
        ("Rain", "🌧️  Rain — Brain dump everything"),
        ("Roots", "🌱  Roots — Ground & find your edge"),
        ("Trunk", "🪵  Trunk — Tools, materials, daily flow"),
        ("Branches", "🌿  Branches — Sales channels"),
        ("Bark", "📖  Bark — Storytelling & voice"),
        ("Leaves", "🍃  Leaves — Products & sales"),
        ("Soil", "🌍  Soil — Reviews, data, nourishment"),
        ("Library", "📚  Library — Rain, SOPs, projects & archive"),
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
    render_tree_progress(section)

    # Replicate structure from index.html project view for Rain, Roots, Bark, Soil:
    # (logo + banner already rendered above) + Brain Dump + Solutions & Processes + Agent + Current Project Notes
    # Rain has its own structure; Roots / Bark / Soil share the rich layout
    if section == "Rain":
        render_rain_page()

    elif section == "Roots":
        render_roots_page()

    elif section in ["Bark", "Soil"]:
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

        solutions_default = data.get("solutions", "")
        if section == "Bark":
            solutions_default = flush_pending_talis_widget("Bark_solutions", solutions_default)
        solutions = st.text_area(
            "Solutions & Processes",
            value=solutions_default,
            height=180,
            key=f"{section}_solutions",
            label_visibility="collapsed",
        )

        agent = data.get("agentComments", "")
        if section == "Soil":
            st.markdown("**Talis**")
            agent_default = flush_pending_talis_widget(
                f"{section}_agent", data.get("agentComments", "")
            )
            agent = st.text_area(
                "Talis",
                value=agent_default,
                height=180,
                key=f"{section}_agent",
                label_visibility="collapsed",
                placeholder="Talis may leave a brief note here — warm, practical, no pressure.",
            )
            with st.expander("Inventory"):
                st.markdown(
                    "**Which were your favorite products from this collection?**\n\n"
                    "**What items did you enjoy making most?**\n\n"
                    "**What was your least favorite item to work on?**  \n"
                    "Are you willing to put this item through the system again?"
                )

        if section in talis_chips:
            snap = {"brainDump": brain, "solutions": solutions}
            if section == "Soil":
                snap["agentComments"] = agent
            render_talis_chips(section, talis_chips[section], snap, num_cols=4)

            if section == "Bark":
                with st.expander("Talis Guide"):
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

        llama_host = get_llama_cpp_host()
        if section == "Bark":
            run_ask_talis(
                "Bark",
                llama_host=llama_host,
                snapshot={"brainDump": brain, "solutions": solutions},
                widget_key="Bark_solutions",
                save_to_page=lambda t: st.session_state.page_content["Bark"].update(
                    {"solutions": t}
                ),
                fallback=lambda: "One channel, one story — start where your energy is highest.",
            )
        elif section == "Soil":
            run_ask_talis(
                "Soil",
                llama_host=llama_host,
                snapshot={"brainDump": brain, "solutions": solutions, "agentComments": agent},
                widget_key="Soil_agent",
                save_to_page=lambda t: st.session_state.page_content["Soil"].update(
                    {"agentComments": t}
                ),
                fallback=lambda: "Soil feeds the next rain — one honest review at a time.",
            )

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

        if section == "Soil":
            render_return_to_grove_button("Soil")

    elif section == "Trunk":
        render_trunk_page()

    elif section == "Library":
        render_library_page()

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

        branches_default = flush_pending_talis_widget(
            "note_Branches",
            st.session_state.notes_history.get("Branches", ""),
        )
        branches_note = st.text_area(
            "Add anything you want to remember or carry forward",
            branches_default,
            height=200,
            key="note_Branches",
        )

        if "Branches" in talis_chips:
            render_talis_chips(
                "Branches",
                talis_chips["Branches"],
                {"notes": branches_note},
                num_cols=4,
            )
        llama_host = get_llama_cpp_host()
        run_ask_talis(
            "Branches",
            llama_host=llama_host,
            snapshot={"notes": branches_note},
            widget_key="note_Branches",
            save_to_page=lambda t: st.session_state.notes_history.update({"Branches": t}),
            fallback=lambda: "One sales channel at a time — depth beats spread.",
        )

        st.divider()
        if st.button("Save notes for Branches"):
            st.session_state.notes_history["Branches"] = branches_note
            st.success("Saved.")

    elif section == "Leaves":
        render_leaves_page()

    elif section == "Help":
        render_help_page()

    elif section == "Picnic":
        render_picnic_page()

    render_flow_step_nav(section)
    render_back_to_tree_button(section)
