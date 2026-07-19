"""
Sync SQLAlchemy DB layer for the Streamlit frontend.
Reuses models and security from dev/backend/app — only strips the async driver.
"""
import os
import sys
import uuid
import logging
from contextlib import contextmanager
from datetime import date

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, Session

_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dev", "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.models.user import User, UserRole        # noqa: E402
from app.models.patient import Patient            # noqa: E402
from app.models.analysis import Analysis          # noqa: E402
from app.core.database import Base                # noqa: E402
from app.core.security import hash_password, verify_password  # noqa: E402

logger = logging.getLogger(__name__)

# Strip async driver so sync SQLAlchemy can use the same URL
_root = os.path.dirname(os.path.abspath(__file__))
_default = f"sqlite:///{os.path.join(_root, 'dev', 'backend', 'pillsafe.db')}"
DB_URL = os.environ.get("DATABASE_URL", _default).replace("+aiosqlite", "")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

# Import all models so metadata is populated before create_all
import app.models.user      # noqa: F401, E402
import app.models.patient   # noqa: F401, E402
import app.models.analysis  # noqa: F401, E402

Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── Auth ──────────────────────────────────────────────────────────────────────

class AuthError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def db_register(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    dob: date,
) -> dict:
    with get_session() as db:
        if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
            raise AuthError("An account with this email already exists.")
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.PATIENT.value,
            is_active=True,
        )
        db.add(user)
        db.flush()
        db.add(Patient(
            id=str(uuid.uuid4()),
            user_id=user.id,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=dob,
        ))
        return {"id": user.id, "email": user.email, "role": user.role}


def db_login(email: str, password: str) -> dict:
    with get_session() as db:
        user = db.execute(
            select(User).where(User.email == email, User.is_active == True)  # noqa: E712
        ).scalar_one_or_none()
        if not user or not verify_password(password, user.hashed_password):
            raise AuthError("Invalid email or password.")
        p = db.execute(
            select(Patient).where(Patient.user_id == user.id)
        ).scalar_one_or_none()
        return {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "first_name": p.first_name if p else "",
            "last_name": p.last_name if p else "",
            "medications_analyzed": p.medications_analyzed if p else 0,
        }


def db_seed_admin(email: str, password: str) -> dict:
    with get_session() as db:
        user = db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        if user:
            user.role = UserRole.ADMIN.value
            user.is_active = True
        else:
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                hashed_password=hash_password(password),
                role=UserRole.ADMIN.value,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            db.flush()
            db.add(Patient(
                id=str(uuid.uuid4()),
                user_id=user.id,
                first_name="Admin",
                last_name="User",
                date_of_birth=date(1990, 1, 1),
            ))
        db.flush()
        return {"id": user.id, "email": user.email, "role": user.role}


# ── Admin ─────────────────────────────────────────────────────────────────────

def db_get_stats() -> dict:
    with get_session() as db:
        return {
            "total_users": db.execute(
                select(func.count()).select_from(User)
            ).scalar() or 0,
            "active_users": db.execute(
                select(func.count()).select_from(User)
                .where(User.is_active == True)  # noqa: E712
            ).scalar() or 0,
            "total_analyses": db.execute(
                select(func.count()).select_from(Analysis)
            ).scalar() or 0,
            "admin_count": db.execute(
                select(func.count()).select_from(User)
                .where(User.role == UserRole.ADMIN.value)
            ).scalar() or 0,
        }


def db_list_users() -> list:
    with get_session() as db:
        users = db.execute(
            select(User).order_by(User.created_at.desc())
        ).scalars().all()
        result = []
        for u in users:
            p = db.execute(
                select(Patient).where(Patient.user_id == u.id)
            ).scalar_one_or_none()
            result.append({
                "id": u.id,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "first_name": p.first_name if p else "",
                "last_name": p.last_name if p else "",
                "created_at": str(u.created_at)[:10] if u.created_at else "",
            })
        return result


def db_list_analyses(limit: int = 20) -> list:
    with get_session() as db:
        rows = db.execute(
            select(Analysis).order_by(Analysis.created_at.desc()).limit(limit)
        ).scalars().all()
        return [
            {
                "id": a.id,
                "user_id": a.user_id,
                "status": a.status,
                "image_filename": a.image_filename or "No image",
                "ml_enabled": a.ml_pipeline_enabled,
                "created_at": str(a.created_at)[:10] if a.created_at else "",
            }
            for a in rows
        ]


def db_activate_user(user_id: str) -> None:
    with get_session() as db:
        u = db.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()
        if u:
            u.is_active = True


def db_deactivate_user(user_id: str) -> None:
    with get_session() as db:
        u = db.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()
        if u:
            u.is_active = False


def db_change_role(user_id: str, role: str) -> None:
    with get_session() as db:
        u = db.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()
        if u:
            u.role = role


def db_delete_user(user_id: str) -> None:
    with get_session() as db:
        u = db.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()
        if u:
            db.delete(u)


def db_save_analysis(
    user_id: str,
    filename: str | None,
    guidance: str | None,
    status: str = "completed",
) -> None:
    with get_session() as db:
        db.add(Analysis(
            id=str(uuid.uuid4()),
            user_id=user_id,
            status=status,
            image_filename=filename,
            guidance=guidance,
            ml_pipeline_enabled=False,
        ))
        db.flush()
        p = db.execute(
            select(Patient).where(Patient.user_id == user_id)
        ).scalar_one_or_none()
        if p:
            p.medications_analyzed = (p.medications_analyzed or 0) + 1
