from __future__ import annotations
import os, datetime as dt
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from db import init_db, SessionLocal, User, Project, Quest, Feedback, ClusterSummary
from ai import sentiment_score, grade_quality, cluster_feedback, do_next_cards, instant_fix_suggestions
from utils import mk_slug, pseudo_random_color, reward_points, sample_badges

# --- App boot ---
Session = init_db()

st.set_page_config(page_title="IterRate — MVP", page_icon="🚀", layout="wide")

# --- Simple demo auth ---
def login_box():
    st.sidebar.header("Sign in")
    email = st.sidebar.text_input("Email", value=st.session_state.get("email",""))
    pw = st.sidebar.text_input("Password", type="password", value=st.session_state.get("pw",""))
    role = st.sidebar.selectbox("Role", ["founder", "critic"], index=0)
    if st.sidebar.button("Log in"):
        db = Session()
        user = db.query(User).filter_by(email=email, password=pw, role=role).first()
        if not user:
            st.sidebar.error("Invalid credentials. Try the demo accounts in README.")
        else:
            st.session_state["user_id"] = user.id
            st.session_state["role"] = user.role
            st.session_state["email"] = email
            st.session_state["pw"] = pw
            st.experimental_rerun()
        db.close()

def ensure_seed():
    db = Session()
    if db.query(User).count() == 0:
        import seed; seed.seed()
    db.close()

ensure_seed()

if "user_id" not in st.session_state:
    login_box()
    st.stop()

db = Session()
me = db.query(User).get(st.session_state["user_id"])

# --- Sidebar navigation ---
st.sidebar.write(f"Signed in as **{me.name or me.email}** ({me.role})")
page = st.sidebar.radio("Navigate", ["Home", "Projects", "Quests", "Feedback", "Insights", "Leaderboards", "Raids"])

def render_health_gauge(project_id: int):
    N = 200
    fb = db.query(Feedback).join(Quest).filter(Quest.project_id==project_id).order_by(Feedback.created_at.desc()).limit(N).all()
    if not fb:
        st.info("No feedback yet for health gauge.")
        return
    avg_sent = sum(f.sentiment for f in fb)/len(fb)
    density = min(1.0, len(fb)/N)
    health = round(50 + 50*avg_sent * density, 1)  # -1..1 mapped
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=health,
        gauge={'axis': {'range': [0,100]}, 'bar': {'thickness': 0.3}},
        title={'text': "Impact Meter (Site Health)"}
    ))
    st.plotly_chart(fig, use_container_width=True)

if page == "Home":
    st.title("IterRate — Feedback that builds better products, faster.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Points", me.points)
    c2.metric("Streak", f"{me.streak} days")
    c3.metric("Badges", ", ".join(me.badges or []) or "—")
    c4.metric("Role", me.role.capitalize())

    st.write("### Live Projects")
    projects = db.query(Project).all()
    for p in projects:
        with st.expander(f"{p.name}  ·  tags: {', '.join(p.tags or [])}"):
            st.write(p.description or "—")
            render_health_gauge(p.id)

elif page == "Projects":
    st.header("Projects")
    if me.role == "founder":
        with st.form("new_proj"):
            name = st.text_input("Project name")
            desc = st.text_area("Description")
            tags = st.text_input("Tags (comma‑separated)", value="ux,website")
            if st.form_submit_button("Create"):
                if not name.strip():
                    st.error("Name required.")
                else:
                    pr = Project(owner_id=me.id, name=name, slug=mk_slug(name), description=desc, tags=[t.strip() for t in tags.split(",") if t.strip()])
                    db.add(pr); db.commit(); st.success("Project created.")
        st.write("---")

    projs = db.query(Project).all() if me.role=="critic" else db.query(Project).filter_by(owner_id=me.id).all()
    if not projs:
        st.info("No projects yet.")
    for p in projs:
        c1, c2 = st.columns([3,1])
        with c1:
            st.subheader(p.name)
            st.caption(", ".join(p.tags or []))
            st.write(p.description or "—")
        with c2:
            st.write(" ")
            st.button("Open Quests", key=f"openq{p.id}")

elif page == "Quests":
    st.header("Feedback Quests")
    if me.role == "founder":
        my_projects = db.query(Project).filter_by(owner_id=me.id).all()
        if not my_projects:
            st.info("Create a project first.")
        else:
            with st.form("new_quest"):
                proj = st.selectbox("Project", my_projects, format_func=lambda p: p.name)
                title = st.text_input("Title")
                brief = st.text_area("Brief / acceptance criteria")
                tags = st.text_input("Tags (comma‑separated)", value="onboarding,ux")
                reward_type = st.selectbox("Reward type", ["points","cash","token","perk","charity"])
                reward_val = st.number_input("Reward value", min_value=1.0, value=15.0, step=1.0)
                deadline = st.date_input("Deadline", value=dt.date.today() + dt.timedelta(days=7))
                if st.form_submit_button("Create Quest"):
                    q = Quest(project_id=proj.id, title=title, brief=brief,
                              tags=[t.strip() for t in tags.split(",") if t.strip()],
                              reward_type=reward_type, reward_value=reward_val,
                              deadline=dt.datetime.combine(deadline, dt.time(23,59)))
                    db.add(q); db.commit(); st.success("Quest created.")

    # list quests
    quests = db.query(Quest).all() if me.role=="critic" else db.query(Quest).join(Project).filter(Project.owner_id==me.id).all()
    for q in quests:
        with st.expander(f"{q.title}  ·  {q.reward_value} {q.reward_type}"):
            st.write(q.brief or "—")
            st.caption(f"Tags: {', '.join(q.tags or [])} · Deadline: {q.deadline.date() if q.deadline else '—'} · Status: {q.status}")
            if me.role == "critic" and q.status in ("open","active"):
                with st.form(f"fb_{q.id}"):
                    text = st.text_area("Your feedback", height=160, key=f"fbtext{q.id}")
                    if st.form_submit_button("Submit feedback"):
                        if not text.strip():
                            st.error("Please enter feedback.")
                        else:
                            s = sentiment_score(text)
                            g = grade_quality(text)
                            fixes = instant_fix_suggestions(text)
                            fb = Feedback(quest_id=q.id, critic_id=me.id, text=text, sentiment=s,
                                          specificity=g["specificity"], helpfulness=g["helpfulness"],
                                          quality_score=g["quality"], suggestions=fixes)
                            db.add(fb); db.commit()
                            pts = reward_points(g["quality"], q.reward_value)
                            me.points += pts
                            me.badges = sample_badges(me.points)
                            db.commit()
                            st.success(f"Submitted. Earned {pts} points.")

            if me.role == "founder":
                feed = db.query(Feedback).filter_by(quest_id=q.id).order_by(Feedback.created_at.desc()).all()
                if feed:
                    df = pd.DataFrame([{
                        "critic": f"#{f.critic_id}",
                        "sent": round(f.sentiment,2),
                        "spec": round(f.specificity,2),
                        "help": round(f.helpfulness,2),
                        "quality": round(f.quality_score,2),
                        "suggestions": "; ".join(f.suggestions or []),
                        "text": f.text[:160] + ("…" if len(f.text)>160 else "")
                    } for f in feed])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    if st.button(f"Cluster & Summarize (quest #{q.id})"):
                        texts = [f.text for f in feed]
                        res = cluster_feedback(texts, k=min(6, max(2, len(texts)//3 or 2)))
                        for f, label in zip(feed, res["labels"]):
                            f.cluster_id = int(label)
                        db.commit()
                        cards = do_next_cards(res["top_terms"])
                        st.success("Clusters computed.")
                        for c in cards:
                            st.info(f"**{c['title']}**\n{c['action']}\nImpact: {c['impact']} · Effort: {c['effort']}")

elif page == "Feedback":
    st.header("My Feedback")
    my_fb = db.query(Feedback).filter_by(critic_id=me.id).order_by(Feedback.created_at.desc()).all()
    if not my_fb:
        st.info("You haven't submitted feedback yet.")
    else:
        for f in my_fb:
            with st.expander(f"Quest #{f.quest_id} · quality {round(f.quality_score,2)} · sent {round(f.sentiment,2)}"):
                st.write(f.text)
                if f.suggestions:
                    st.caption("Instant Fix‑It: " + "; ".join(f.suggestions))

elif page == "Insights":
    st.header("Insights — Live")
    if me.role != "founder":
        st.info("Insights are for founders. Submit feedback to climb the leaderboard!")
    else:
        my_projects = db.query(Project).filter_by(owner_id=me.id).all()
        if not my_projects:
            st.info("Create a project first.")
        else:
            p = st.selectbox("Project", my_projects, format_func=lambda x: x.name)
            render_health_gauge(p.id)

            all_fb = db.query(Feedback).join(Quest).filter(Quest.project_id==p.id).all()
            if st.button("Recompute clusters across project"):
                texts = [f.text for f in all_fb]
                res = cluster_feedback(texts, k=min(8, max(2, len(texts)//4 or 2)))
                for f, label in zip(all_fb, res["labels"]):
                    f.cluster_id = int(label)
                db.commit()
                cards = do_next_cards(res["top_terms"])
                st.success("Project clusters updated.")
                for c in cards:
                    st.info(f"**{c['title']}**\n{c['action']}\nImpact: {c['impact']} · Effort: {c['effort']}")

elif page == "Leaderboards":
    st.header("Leaderboards")
    critics = db.query(User).filter_by(role="critic").order_by(User.points.desc()).all()
    if not critics:
        st.info("No critics yet. Encourage signups!")
    else:
        df = pd.DataFrame([{"critic": c.name or c.email, "points": c.points, "streak": c.streak, "badges": ", ".join(c.badges or [])} for c in critics])
        st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Raids":
    st.header("Feedback Raids (sprints)")
    st.write("Schedule a 30‑minute sprint to gather 10+ reviews fast. Demo only.")
    if me.role == "founder":
        with st.form("raid_form"):
            title = st.text_input("Raid name", value="Honest Hour — Onboarding")
            when = st.date_input("Date", value=dt.date.today() + dt.timedelta(days=1))
            time = st.time_input("Time", value=dt.time(17, 0))
            min_reviewers = st.number_input("Min reviewers", 5, 50, 10)
            reward_boost = st.slider("Reward boost ×", 1.0, 3.0, 1.5, 0.1)
            if st.form_submit_button("Create Raid"):
                st.success(f"Raid scheduled: {title} on {when} at {time}. Reward boost ×{reward_boost}. (Demo)")

st.sidebar.write("---")
if st.sidebar.button("Sign out"):
    for k in ["user_id","role","email","pw"]:
        st.session_state.pop(k, None)
    st.experimental_rerun()
