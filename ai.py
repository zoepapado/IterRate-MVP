from __future__ import annotations
from typing import List, Dict, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from nltk.sentiment import SentimentIntensityAnalyzer

# Initialize global (lazy)
_VECT = None
_SIA = None

def _get_sia():
    global _SIA
    if _SIA is None:
        _SIA = SentimentIntensityAnalyzer()
    return _SIA

def sentiment_score(text: str) -> float:
    if not text.strip():
        return 0.0
    sia = _get_sia()
    s = sia.polarity_scores(text)
    return float(s.get("compound", 0.0))

def grade_quality(text: str) -> Dict[str, float]:
    # Very naive quality grading:
    # - specificity: penalize short feedback and generic words
    # - helpfulness: reward presence of verbs like 'change', 'add', 'remove', 'because', 'should'
    t = text.lower()
    length_score = min(len(t) / 300.0, 1.0)
    generic_penalty = sum(int(w in t) for w in ["good", "bad", "nice", "cool", "great"])
    specificity = max(0.0, length_score - 0.1 * generic_penalty)

    helpful_terms = ["change", "add", "remove", "because", "should", "consider", "instead", "confusing", "unclear", "rename", "button", "cta", "contrast", "align", "spacing", "onboarding"]
    helpfulness = min(1.0, sum(1 for w in helpful_terms if w in t) / 6.0)

    quality = 0.6 * specificity + 0.4 * helpfulness
    return {"specificity": specificity, "helpfulness": helpfulness, "quality": quality}

def cluster_feedback(texts: List[str], k: int = 4) -> Dict[str, Any]:
    """
    Offline clustering of feedback with TF‑IDF + KMeans.
    Returns labels and top terms per cluster for semantics.
    """
    if not texts:
        return {"labels": [], "top_terms": {}}
    vect = TfidfVectorizer(ngram_range=(1,2), min_df=1, stop_words="english")
    X = vect.fit_transform(texts)
    k = min(k, max(1, X.shape[0]))
    model = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = model.fit_predict(X)
    # top terms per cluster
    order_centroids = model.cluster_centers_.argsort()[:, ::-1]
    terms = np.array(vect.get_feature_names_out())
    top_terms = {i: terms[order_centroids[i, :8]].tolist() for i in range(k)}
    return {"labels": labels.tolist(), "top_terms": top_terms}

def do_next_cards(cluster_terms: Dict[int, List[str]]) -> List[Dict[str, Any]]:
    """
    Map cluster keywords into actionable cards (impact/effort are heuristic).
    """
    cards = []
    for cid, terms in cluster_terms.items():
        title = f"Issue Cluster #{cid}: " + ", ".join(terms[:3])
        action = f"Investigate and address issues related to: {', '.join(terms[:6])}."
        impact = round(0.6 + 0.4 * (1.0 - cid / (len(cluster_terms) or 1)), 2)  # silly heuristic
        effort = round(0.3 + 0.2 * (cid / (len(cluster_terms) or 1)), 2)
        cards.append({"cluster_id": cid, "title": title, "action": action, "impact": impact, "effort": effort})
    return cards

def instant_fix_suggestions(text: str) -> List[str]:
    """
    Suggest quick fixes based on patterns.
    """
    t = text.lower()
    fixes = []
    if "button" in t or "cta" in t:
        fixes.append("Try a higher‑contrast primary CTA and place it above the fold.")
    if "signup" in t or "sign up" in t or "onboarding" in t:
        fixes.append("Reduce onboarding steps to 2–3 screens; add a progress indicator.")
    if "readable" in t or "font" in t or "contrast" in t:
        fixes.append("Increase base font to 16–18px, check WCAG AA color contrast.")
    if "confusing" in t or "unclear" in t:
        fixes.append("Rewrite labels with verbs and add helper text or examples.")
    return fixes[:3]
