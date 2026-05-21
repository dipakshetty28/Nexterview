from fastapi import FastAPI

from app.api.interviews import router as interview_router
from app.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Nexterview API")
app.include_router(interview_router)


@app.get("/health")
def health():
    return {"status": "ok"}
