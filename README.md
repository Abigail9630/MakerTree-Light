# MakerTree-Light

Streamlit app for the Maker Tree — a creative workflow for makers (Rain → Roots → Trunk → Branches → Bark → Leaves → Soil → Picnic).

**X Prize submission (light edition).** Work in progress.

## Run locally

```bash
cd MakerTree-Light
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run maker_tree_app.py
```

Or: `./run.sh`

Opens in your browser (phone or laptop).

## What’s here

- `maker_tree_app.py` — main app
- `assets/` — tree images, section banners, logo
- `Rose.md` — project vision notes
- `Google Tools/Products.md` — Google dependencies (fonts, Gemini API)
- `LICENSE` — MIT (simple “use with credit” license)

## First time on GitHub? (the toggles)

When you click **New repository** on GitHub, you’ll see three optional checkboxes. **Leave all three OFF** — you already have these files on your computer:

| GitHub toggle | Turn it on? | Why |
|---------------|-------------|-----|
| **Add a README** | **No** | `README.md` is already in this folder |
| **Add .gitignore** | **No** | `.gitignore` is already here (keeps `.venv` and secrets out) |
| **Choose a license** | **No** | `LICENSE` is already here (MIT) |

Then create the empty repo, and push from your machine (see below).

## Push to GitHub (copy-paste)

```bash
cd ~/Desktop/MakerTree-Light

git add -A
git commit -m "MakerTree-Light — initial Streamlit app"

git remote add origin https://github.com/YOUR_USERNAME/MakerTree-Light.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

**Git identity (use the MakerTree email):**

```bash
git config user.email "MakerTreeApp@gmail.com"
git config user.name "MakerTree App"
```

Those two lines apply only to this repo folder (not your whole computer). Then commit and push as above.

## Notes

- Picnic section still rough.
- Sycamore Grove Google Form URL is a placeholder until the live form is linked.
- Gemini API key: optional for most flow; one call on Roots for X Prize compliance when you add a key.
- Never commit API keys — `.gitignore` blocks `.env` and Streamlit secrets.

More polish tomorrow. Good enough for tonight.
