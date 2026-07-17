from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import timedelta
from pydantic import BaseModel
import json

from app.db.session import get_db
from app.models.user import User
from app.models.role import Role
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.config import settings
from app.models.permission import Permission
from app.models.associations import user_roles, role_permissions
from app.api.deps import get_current_user
from app.core.cache import get_redis

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    # find user by email
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(User.email == login_data.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # verify password
    password = login_data.password.strip()

    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # get user permissions
    result = await db.execute(
        select(Permission.name)
        .join(role_permissions, Permission.id == role_permissions.c.permission_id)
        .join(user_roles, role_permissions.c.role_id == user_roles.c.role_id)
        .where(user_roles.c.user_id == user.id)
        .distinct()
    )

    permissions = [row[0] for row in result.fetchall()]

    # create access token
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    access_token = create_access_token(
        data={"sub": str(user.id), "perms": permissions},
        expires_delta=access_token_expires,
    )

    return TokenResponse(access_token=access_token)

@router.get("/me")
async def read_current_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    # check redis cache before querying db
    cache_key = f"user:{current_user.id}:details"
    cached_data = await redis_client.get(cache_key)
    
    # cache hit
    if cached_data:
        return json.loads(cached_data)
    # on cache miss
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(User.id == current_user.id)
    )
    user_with_roles = result.scalar_one()

    # Get permissions from token (already attached by get_current_user)
    permissions = current_user.permissions if hasattr(current_user, 'permissions') else []

    # Get user role from database
    user_role = user_with_roles.roles[0].name

    response = {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "role": user_role,
        "permissions": permissions,
    }
    await redis_client.setex(cache_key, 600, json.dumps(response)) # 10 minutes TTL

    return response

@router.post("/register")
async def register_user(
    register_data: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == register_data.email)
    )

    result = result.scalar_one_or_none()

    if result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Get the viewer role
    viewer_role_result = await db.execute(
        select(Role).where(Role.name == "viewer")
    )
    viewer_role = viewer_role_result.scalar_one_or_none()

    if not viewer_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default viewer role not found."
        )

    # Create new user
    hashed_pw = get_password_hash(register_data.password)

    new_user = User(
        email=register_data.email,
        full_name=register_data.full_name,
        hashed_password=hashed_pw,
        is_active=True,
    )

    # Assign viewer role to new user
    new_user.roles.append(viewer_role)

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {
        "message": "User registered successfully with viewer role",
        "user_id": str(new_user.id),
        "full_name": new_user.full_name,
        "role": "viewer"
    }
