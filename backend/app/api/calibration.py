from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require_roles
from app.models.user import User, UserRole
from app.schemas.calibration import CalibrationSessionRead
from app.services.calibration import get_calibration_sessions

router = APIRouter(prefix="/api/calibration", tags=["calibration"])


@router.get("", response_model=list[CalibrationSessionRead])
def list_calibration_sessions(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
) -> list[CalibrationSessionRead]:
    _ = current_user
    return get_calibration_sessions()
