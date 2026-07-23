"""Seed 5 test patient profiles with the 15 NB07 OTC DINs (3 confirmed DINs each).

Run from dev/backend with its venv:
    cd dev/backend && venv\\Scripts\\python.exe scripts/seed_test_profiles.py

Idempotent: re-running deletes and recreates the same 5 test accounts
(matched by email, all under @test.com).
"""

import asyncio
import sys
from datetime import date
from pathlib import Path

# This script lives in dev/backend/scripts/ -- add dev/backend itself (the
# script's parent directory) to sys.path so `import app...` resolves
# regardless of the caller's current working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select

import importlib
import pkgutil

import app.models as _models

for _m in pkgutil.iter_modules(_models.__path__):
    importlib.import_module(f"app.models.{_m.name}")

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.user import User, UserRole

PASSWORD = "PillSafe1"

# (email, first, last, dob, lang, [(din8, drug_name, dosage, purpose, slots, times)])
PROFILES = [
    ("margaret@test.com", "Margaret", "Miller", date(1948, 3, 14), "en", [
        ("00013803", "GRAVOL TABLETS", "50 mg", "Nausea", ["morning"], ["08:00"]),
        ("00559407", "TYLENOL EXTRA STRENGTH", "500 mg", "Pain relief", ["morning", "evening"], ["08:00", "20:00"]),
        ("02237726", "ASPIRIN 81MG", "81 mg", "Heart health", ["morning"], ["08:00"]),
    ]),
    ("henri@test.com", "Henri", "Tremblay", date(1951, 7, 2), "fr", [
        ("01933558", "ADVIL TABLETS", "200 mg", "Pain relief", ["morning", "evening"], ["09:00", "21:00"]),
        ("00026123", "SENOKOT S", "8.6 mg", "Constipation", ["evening"], ["21:00"]),
        ("02273357", "MAXIMUM STRENGTH PEPCID AC", "20 mg", "Heartburn", ["evening"], ["18:00"]),
    ]),
    ("fatima@test.com", "Fatima", "Khan", date(1954, 11, 23), "en", [
        ("02017849", "BENADRYL ALLERGY", "25 mg", "Allergies", ["evening"], ["20:00"]),
        ("02242658", "MOTRIN 400MG", "400 mg", "Pain relief", ["morning"], ["08:00"]),
        ("00254142", "DULCOLAX", "5 mg", "Constipation", ["evening"], ["21:00"]),
    ]),
    ("wei@test.com", "Wei", "Chen", date(1950, 1, 30), "en", [
        ("02362430", "NAPROXEN", "220 mg", "Pain relief", ["morning", "evening"], ["08:00", "20:00"]),
        ("02273462", "BENYLIN EXTRA STRENGTH COLD & SINUS DAY", "", "Cold & sinus (day)", ["morning", "afternoon"], ["08:00", "14:00"]),
        ("02230790", "MUSCLE & BACK PAIN RELIEF CAPLETS", "", "Back pain", ["morning"], ["09:00"]),
    ]),
    ("rosa@test.com", "Rosa", "Alvarez", date(1957, 5, 9), "en", [
        ("02375990", "ALLERGY REMEDY", "10 mg", "Allergies", ["morning"], ["08:00"]),
        ("02306409", "BENYLIN EXTRA STRENGTH COLD & SINUS NIGHT", "", "Cold & sinus (night)", ["evening"], ["21:00"]),
        ("02256452", "DIARRHEA RELIEF", "2 mg", "Diarrhea", ["morning"], ["08:00"]),
    ]),
]


async def main():
    async with AsyncSessionLocal() as db:
        for email, first, last, dob, lang, meds in PROFILES:
            existing = (
                await db.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if existing:
                pat = (
                    await db.execute(select(Patient).where(Patient.user_id == existing.id))
                ).scalar_one_or_none()
                if pat:
                    await db.execute(
                        delete(Prescription).where(Prescription.patient_id == pat.id)
                    )
                    await db.delete(pat)
                await db.delete(existing)
                await db.flush()

            user = User(
                email=email,
                hashed_password=hash_password(PASSWORD),
                role=UserRole.PATIENT.value,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.flush()

            patient = Patient(
                user_id=user.id,
                first_name=first,
                last_name=last,
                date_of_birth=dob,
                preferred_language=lang,
            )
            db.add(patient)
            await db.flush()

            for din, name, dosage, purpose, slots, times in meds:
                db.add(
                    Prescription(
                        patient_id=patient.id,
                        drug_name=name,
                        dosage=dosage or None,
                        frequency_text="Once daily" if len(times) == 1 else "Twice daily",
                        frequency_type="daily",
                        time_slots=slots,
                        specific_times=times,
                        purpose=purpose,
                        is_active=True,
                        din=din,
                        din_confirmed=True,
                    )
                )
            print(f"seeded {email} ({first} {last}, {lang}) with {len(meds)} confirmed DINs")

        await db.commit()

    # verify
    async with AsyncSessionLocal() as db:
        for email, *_ in PROFILES:
            user = (await db.execute(select(User).where(User.email == email))).scalar_one()
            pat = (await db.execute(select(Patient).where(Patient.user_id == user.id))).scalar_one()
            rx = (
                await db.execute(select(Prescription).where(Prescription.patient_id == pat.id))
            ).scalars().all()
            dins = sorted(r.din for r in rx)
            assert all(r.din_confirmed and r.is_active for r in rx), email
            print(f"VERIFIED {email}: {len(rx)} active confirmed prescriptions {dins}")


asyncio.run(main())
