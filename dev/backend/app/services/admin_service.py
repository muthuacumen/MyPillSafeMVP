from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.user import User, UserRole
from app.models.analysis import Analysis


async def list_users(
    db: AsyncSession, skip: int = 0, limit: int = 50
) -> list[User]:
    result = await db.execute(
        select(User)
        .options(selectinload(User.patient))
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_user_by_id_admin(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(
        select(User)
        .options(selectinload(User.patient))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def set_user_active(
    db: AsyncSession, user_id: str, is_active: bool
) -> User | None:
    user = await get_user_by_id_admin(db, user_id)
    if not user:
        return None
    user.is_active = is_active
    await db.flush()
    return user


async def delete_user(db: AsyncSession, user_id: str) -> bool:
    user = await get_user_by_id_admin(db, user_id)
    if not user:
        return False
    await db.delete(user)
    await db.flush()
    return True


async def update_user_role(
    db: AsyncSession, user_id: str, role: str
) -> User | None:
    user = await get_user_by_id_admin(db, user_id)
    if not user:
        return None
    user.role = role
    await db.flush()
    return user


async def list_all_analyses(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[Analysis]:
    result = await db.execute(
        select(Analysis)
        .order_by(Analysis.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_platform_stats(db: AsyncSession) -> dict:
    total_users = await db.scalar(select(func.count(User.id))) or 0
    active_users = (
        await db.scalar(
            select(func.count(User.id)).where(User.is_active == True)  # noqa: E712
        )
    ) or 0
    admin_count = (
        await db.scalar(
            select(func.count(User.id)).where(User.role == UserRole.ADMIN.value)
        )
    ) or 0
    total_analyses = await db.scalar(select(func.count(Analysis.id))) or 0
    return {
        "total_users": total_users,
        "active_users": active_users,
        "admin_count": admin_count,
        "total_analyses": total_analyses,
    }
