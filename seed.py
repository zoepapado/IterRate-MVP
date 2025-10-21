from __future__ import annotations
import datetime as dt
from db import init_db, SessionLocal, User, Project, Quest
from utils import mk_slug

def seed():
    init_db()
    db = SessionLocal()
    # users
    founder = User(email="founder@demo.io", password="demo", role="founder", name="Demo Founder")
    critic  = User(email="critic@demo.io",  password="demo", role="critic",  name="Demo Critic")
    db.add_all([founder, critic]); db.commit()

    # project
    proj = Project(owner_id=founder.id, name="Camden Records Landing", slug=mk_slug("Camden Records Landing"),
                   description="Music studio landing page and booking flow.", tags=["music","studio","booking"])
    db.add(proj); db.commit()

    # quests
    q1 = Quest(project_id=proj.id, title="Fix our onboarding",
               brief="Users drop off after choosing time slots. Find friction and propose changes.",
               tags=["onboarding","booking","ux"], reward_type="points", reward_value=25,
               deadline=dt.datetime.utcnow() + dt.timedelta(days=7))
    q2 = Quest(project_id=proj.id, title="Landing page vibe check",
               brief="Is the value prop clear in 5 seconds? How would you rewrite the hero?",
               tags=["copy","hero","clarity"], reward_type="points", reward_value=15,
               deadline=dt.datetime.utcnow() + dt.timedelta(days=5))
    db.add_all([q1, q2]); db.commit()
    db.close()
    print("Seeded demo data.")

if __name__ == "__main__":
    seed()
