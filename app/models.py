from sqlalchemy import Column, Integer, String, Text, ForeignKey
from .database import Base


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    role_title = Column(String(255), nullable=False)
    stack = Column(String(255), nullable=False)
    difficulty = Column(String(64), nullable=False)
    interview_type = Column(String(128), nullable=False)
    duration_minutes = Column(Integer, nullable=False)


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    business_context = Column(Text, nullable=False)
    technical_requirements = Column(Text, nullable=False)
    starter_code = Column(Text, nullable=False)
    expected_behavior = Column(Text, nullable=False)
    logs_or_bug_report = Column(Text, nullable=False)
    hidden_evaluation_points = Column(Text, nullable=False)
    candidate_instructions = Column(Text, nullable=False)
    interviewer_rubric = Column(Text, nullable=False)
