from pydantic import BaseModel

from app.schemas.auth import OrganizationMembershipRead, UserRead


class DashboardResponse(BaseModel):
    user: UserRead
    organizations: list[OrganizationMembershipRead]
