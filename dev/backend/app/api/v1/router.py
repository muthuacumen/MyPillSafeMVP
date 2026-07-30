from fastapi import APIRouter
from app.api.v1.routes import (
    admin,
    auth,
    contact,
    dev,
    instructions,
    patients,
    pill,
    prescriptions,
    qa,
    reference,
    reminders,
    scans,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(patients.router)
api_router.include_router(pill.router)
api_router.include_router(prescriptions.router)
api_router.include_router(reference.router)
api_router.include_router(qa.router)
api_router.include_router(reminders.router)
api_router.include_router(instructions.router)
api_router.include_router(scans.router)
api_router.include_router(contact.router)
api_router.include_router(admin.router)
api_router.include_router(dev.router)
