from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, insert
from typing import List, Optional
from uuid import UUID

from app.api.deps import get_current_user
from app.db.session import get_db
from app.core.cache import get_redis
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.associations import user_roles, role_permissions

router = APIRouter()

class UserResponse(BaseModel):
    user_id: UUID
    user_email: str
    user_name: str
    role_id: Optional[int]
    role_name: Optional[str]

# get list of users and their details
@router.get("", response_model=List[UserResponse])
async def get_all_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if "read:users" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No read:users permission"
        )

    result = await db.execute(
        select(User, Role.id, Role.name)
        .outerjoin(user_roles, User.id == user_roles.c.user_id)
        .outerjoin(Role, user_roles.c.role_id == Role.id)
        .order_by(User.email)
    )

    rows = result.all()

    users_list = []
    for r in rows:
        user, role_id, role_name = r
        user_response = UserResponse(
            user_id=user.id,
            user_email=user.email, 
            user_name=user.full_name, 
            role_id=role_id, 
            role_name=role_name)
        
        users_list.append(user_response)

    return users_list

# updates a given users role
@router.put("/{user_id}/role")
async def update_user(
    user_id: UUID,
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    if "write:roles" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No write:roles permission"
        )
    
    # validate user to change exists
    user = await db.execute(
        select(User)
        .where(User.id == user_id)
    )

    user = user.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not exist"
        )
    
    # validate new role exists
    role = await db.execute(
        select(Role)
        .where(Role.id == role_id)
    )

    role = role.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role does not exist"
        )

    # check for self demotion 
    if current_user.id == user_id:
        # Check if new role has write:roles permission
        role_perms_result = await db.execute(
            select(Permission.name)
            .join(role_permissions, Permission.id == role_permissions.c.permission_id)
            .where(role_permissions.c.role_id == role.id)
        )
        new_role_permissions = [row[0] for row in role_perms_result.fetchall()]

        if "write:roles" not in new_role_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot remove your own write:roles permission"
            )
        
    # update user_roles table
    await db.execute(
        delete(user_roles)
        .where(user_roles.c.user_id == user_id)
    )
    await db.execute(
        insert(user_roles)
        .values(user_id=user_id, role_id=role_id)
    )
    await db.commit()

    # delete cached data
    cache_key = f"user:{user.id}:details"
    await redis_client.delete(cache_key)

    return {
        "message": "User role updated successfully",
        "user_email": user.email,
        "user_name": user.full_name,
        "new_role": role.name
    }
