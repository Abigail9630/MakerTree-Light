# Google Products Used in MakerTree-Beta

This document tracks Google products used in **MakerTree-Beta** (Streamlit edition of MakerTree). For X Prize submission transparency.

## Google Fonts

- **Product**: Google Fonts (via fonts.googleapis.com CDN)
- **Specific Fonts Used**:
  - Inter (sans-serif): Weights 500 (medium), 600 (semi-bold), 700 (bold), 800 (extra-bold).
    - Used for: Body text, headings, UI elements (buttons, labels, text areas).
    - Reason: Provides heavier font weights and better readability on mobile devices and in dark themes compared to previous lighter fonts (e.g., Instrument Sans). Base font-size increased to 19px (21px on small screens via media queries) with font-weight 500 default.
  - Instrument Serif (serif): Weights 600 (semi-bold), 700 (bold).
    - Used for: Logo text styling in the header (paired with the circular logo image).
- **Integration**:
  - Loaded via CSS `@import` in custom styles (injected into Streamlit via `st.markdown` with `unsafe_allow_html=True`).
  - Ensures offline fallbacks via system-ui and -apple-system.
  - Applied globally to html, body, markdown, text areas, buttons, subheaders, etc.
- **URL Example** (as of last update):
  `https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800&family=Instrument+Serif:wght@600;700&display=swap`
- **Date Added/Updated**: 2026-06-13 (as part of font readability improvements for phone use and dark themes).
- **Notes**: This is the primary Google dependency for typography. No local font files are hosted yet (CDN for simplicity and performance). For full offline Xprize compliance, local WOFF2 hosting can be added later.

## Google Gemini (AI Image Generation)

- **Product**: Google Gemini (Gemini AI image generator, formerly Imagen or similar within Gemini ecosystem).
- **Usage**:
  - Generated the primary circular app logo: `maker-tree-logo.png` (1024x1024 PNG, RGBA).
  - Location: `assets/images/maker-tree-logo.png` (copied from original MakerTree/assets for consistency).
- **How Implemented**:
  - Used as the main logo at the top of every page in the Streamlit app.
  - Rendered via base64 embedding in custom HTML/CSS (circular shape maintained with `border-radius: 50%`, `object-fit: cover`, and green border to match app theme).
  - Replaces previous emoji-based or SVG tree logos (e.g., 🌳) for a more professional, branded appearance.
  - Also used in the rich HTML version (Desktop/MakerTree) for consistency.
- **Date Generated/Added**: Recently (Gemini image file timestamp aligns with logo implementation around 2026-06-13).
- **Notes**: The logo maintains a circular design as per requirements. This is a creative asset, not runtime dependency. For Xprize, note that Gemini was used for asset creation only.

## Other Notes on Google Dependencies
- No other Google products are currently used in MakerTree-Beta.
- The app is designed to be lightweight and local-first (Streamlit with minimal external calls).
- Fonts load from Google CDN for ease, but the core functionality (navigation, editable sections for Rain/Roots/etc., local model stubs) does not require Google services at runtime.
- If additional Google tools are integrated in the future (e.g., for AI features in Roots section), they will be documented here immediately.
- For full offline mode in Xprize judging: Consider self-hosting fonts and avoiding any CDN calls.

## Google Gemini (Generative AI API)

- **Product**: Google Gemini API (via google-generativeai Python SDK, models like gemini-1.5-flash or gemini-1.5-pro).
- **Usage**:
  - Provides the required at least one Gemini API call for Xprize rules compliance.
  - Integrated in the Roots section for parsing brain dumps: extracts ideas, identifies competitive advantage, generates gentle follow-up questions based on guardrails (no bombardment, only on hesitation, key questions for disregarded ideas, etc.).
  - Fallback: Local model stub (TinyLlama/Phi-2 style) remains available; Gemini is the "polish" / required call.
- **Integration**:
  - API key provided via Streamlit text_input (for now; will use env var or secrets in final).
  - Prompt engineering for guardrails: "Act as gentle homesteading agent. Parse this brain dump for competitive advantages. Only ask 1-2 gentle questions if hesitation detected. Use this key question for disregarded ideas: 'Is there a tool/material/skill that you have not used before and want to try?'"
  - Response parsed and inserted into the structured page (Brain Dump + Agent comments).
- **Date Added/Updated**: 2026-06-13 (implementation in progress during focused Xprize push).
- **Notes**: This fulfills the Xprize requirement for at least one Gemini API call. The app remains primarily local-first (Gemma or other local model as default). Full prompt and call code will be in maker_tree_app.py. Cost: ~$20/month plan recommended for development speed and quota.

This file should be kept updated with every Google-related addition. Last updated: 2026-06-13 by Violet (coding specialist). (Gemini API integration added to Roots for Xprize compliance.)
