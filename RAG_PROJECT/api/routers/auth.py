"""Authentication endpoints: register, login, me."""
from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import require_user
from api.schemas import LoginRequest, RegisterRequest, TokenResponse, UserInfo
from services.user_store import User, authenticate_user, create_user, username_exists
from utils.security import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest):
    if username_exists(req.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在",
        )
    user = create_user(req.username, req.password, role="user")
    token = create_access_token({"sub": user.user_id, "role": user.role})
    return TokenResponse(access_token=token, role=user.role, username=user.username)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_access_token({"sub": user.user_id, "role": user.role})
    return TokenResponse(access_token=token, role=user.role, username=user.username)


@router.get("/me", response_model=UserInfo)
async def me(user: User = Depends(require_user)):
    return UserInfo(
        user_id=user.user_id,
        username=user.username,
        role=user.role,
        created_at=user.created_at,
    )
