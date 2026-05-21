from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Interview, Scenario
from app.schemas import ScenarioResponse
from app.services.scenario_generator import generate_scenario_structured

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


@router.post("/{interview_id}/generate-scenario", response_model=ScenarioResponse)
def generate_scenario(interview_id: int, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    scenario = generate_scenario_structured(
        role=interview.role_title,
        stack=interview.stack,
        difficulty=interview.difficulty,
        interview_type=interview.interview_type,
        duration=interview.duration_minutes,
    )

    row = Scenario(interview_id=interview_id, **scenario.model_dump())
    db.add(row)
    db.commit()

    return ScenarioResponse(interview_id=interview_id, **scenario.model_dump())
