from __future__ import annotations
import os, datetime as dt
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean, JSON
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///iterate.db")

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)  # demo only
    role = Column(String, nullable=False)      # "founder" or "critic"
    name = Column(String, nullable=False, default="")
    points = Column(Integer, default=0)
    streak = Column(Integer, default=0)
    badges = Column(JSON, default=list)        # ["Early Bird", ...]
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    projects = relationship("Project", back_populates="owner")
    feedback = relationship("Feedback", back_populates="critic")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    description = Column(Text, default="")
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    quests = relationship("Quest", back_populates="project", cascade="all, delete-orphan")

class Quest(Base):
    __tablename__ = "quests"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    title = Column(String, nullable=False)
    brief = Column(Text, default="")
    tags = Column(JSON, default=list)
    reward_type = Column(String, default="points")   # points|cash|token|perk|charity
    reward_value = Column(Float, default=10.0)
    deadline = Column(DateTime, nullable=True)
    status = Column(String, default="open")          # open|active|closed
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    project = relationship("Project", back_populates="quests")
    feedback = relationship("Feedback", back_populates="quest", cascade="all, delete-orphan")

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True)
    quest_id = Column(Integer, ForeignKey("quests.id"))
    critic_id = Column(Integer, ForeignKey("users.id"))
    text = Column(Text, nullable=False)
    sentiment = Column(Float, default=0.0)           # -1..1
    specificity = Column(Float, default=0.0)         # 0..1
    helpfulness = Column(Float, default=0.0)         # 0..1
    quality_score = Column(Float, default=0.0)       # composite
    cluster_id = Column(Integer, nullable=True)
    suggestions = Column(JSON, default=list)         # "Instant Fix‑It"
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    quest = relationship("Quest", back_populates="feedback")
    critic = relationship("User", back_populates="feedback")

class ClusterSummary(Base):
    __tablename__ = "cluster_summaries"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    quest_id = Column(Integer, ForeignKey("quests.id"), nullable=True)
    cluster_id = Column(Integer, nullable=False)
    title = Column(String, default="")
    summary = Column(Text, default="")
    do_next = Column(JSON, default=list)     # [{action, impact, effort}]
    updated_at = Column(DateTime, default=dt.datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
    return SessionLocal
