import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Boolean, DateTime, Enum, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class UserRole(str, PyEnum):
    PATIENT = "PATIENT"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.PATIENT.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Real session termination (Task T2). Minted into every access/refresh
    # token's `tv` claim; validation (app/api/deps.py, auth_service.refresh_
    # tokens) 401s any token whose `tv` doesn't match the live column. Bumping
    # this is what actually kills sessions already issued -- unlike is_active,
    # which only blocks NEW logins/refreshes, this invalidates tokens a user
    # is already holding. Default 0 so every pre-existing user/token keeps
    # working until an admin explicitly terminates a session.
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    patient: Mapped["Patient"] = relationship(  # noqa: F821
        "Patient", back_populates="user", uselist=False, lazy="select",
        cascade="all, delete-orphan",
    )
    analyses: Mapped[list["Analysis"]] = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")  # noqa: F821

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
