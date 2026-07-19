from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class PatientUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    preferred_language: str | None = None
    notifications_enabled: bool | None = None


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    first_name: str
    last_name: str
    date_of_birth: date
    preferred_language: str
    phone_number: str | None
    medications_analyzed: int
    last_scan_at: datetime | None
    notifications_enabled: bool
    created_at: datetime


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
