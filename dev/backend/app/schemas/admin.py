from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator
from app.models.user import UserRole


class PatientBasicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str
    last_name: str
    medications_analyzed: int


class UserListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    patient: PatientBasicOut | None = None


class PlatformStats(BaseModel):
    total_users: int
    active_users: int
    total_analyses: int
    admin_count: int


class RoleUpdate(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        valid = {r.value for r in UserRole}
        if v not in valid:
            raise ValueError(f"Role must be one of: {', '.join(valid)}")
        return v


class AnalysisSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    status: str
    image_filename: str | None
    guidance: str | None
    ml_pipeline_enabled: bool
    created_at: datetime
