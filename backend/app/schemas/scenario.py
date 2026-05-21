from pydantic import BaseModel


class GeneratedScenarioSchema(BaseModel):
    title: str
    business_context: str
    technical_requirements: str
    starter_code: str
    expected_behavior: str
    logs_or_bug_report: str
    hidden_evaluation_points: str
    candidate_instructions: str
    interviewer_rubric: str


class ScenarioResponse(GeneratedScenarioSchema):
    id: int
    interview_id: int
