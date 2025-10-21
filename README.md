# IterRate (MVP) — Streamlit + SQLite

A functional prototype of **IterRate** — a two‑sided, gamified product‑feedback marketplace with AI‑assisted clustering and actionable summaries.  
Front‑end: Streamlit. Storage: SQLite via SQLAlchemy. Optional offline NLP (TF‑IDF + KMeans) and VADER sentiment.

## Features
- **Two roles**: Founders (create projects & feedback quests) and Critics (complete missions for rewards).
- **Feedback Quests**: task briefs with tags, rewards, and deadlines.
- **AI layer (offline)**: TF‑IDF + KMeans clustering; VADER sentiment; "Do‑Next" cards.
- **Quality grading**: scores feedback specificity/helpfulness to rank rewards.
- **Impact Meter**: live site‑health gauge from rolling sentiment & issue density.
- **Leaderboards**: points, streaks, badges.
- **Feedback Raids**: 10‑critics‑in‑30‑minutes style sprint (scheduled rounds).
- **Instant Fix‑It suggestions**: copy/UX hints based on patterns in clusters.

> No external APIs are required. If you want to swap in OpenAI embeddings/summaries, add your calls in `ai.py` (hooks included).

## Quickstart
```bash
# 1) Create venv (recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2) Install
pip install -r requirements.txt

# 3) (One‑time) download VADER lexicon for sentiment
python -c "import nltk; nltk.download('vader_lexicon')"

# 4) Run
streamlit run app.py
```

## Default Demo Users
- Founder: `founder@demo.io` / password `demo`
- Critic:  `critic@demo.io`  / password `demo`

## Project Structure
```
iterate_app/
├─ app.py               # Streamlit UI & routing
├─ db.py                # SQLAlchemy models & session
├─ ai.py                # Clustering, sentiment, grading, action cards
├─ seed.py              # Seed sample data
├─ utils.py             # Helpers
├─ requirements.txt
└─ README.md
```

## Notes
- This is an MVP to showcase core loops and data flow, not a hardened production system.
- Swap SQLite for Postgres easily by updating `DATABASE_URL` in `db.py`.
- Add authentication (e.g., Firebase, Auth0) later; a simple demo auth is bundled.
