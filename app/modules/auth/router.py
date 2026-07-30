from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, RefreshTokenRequest
from app.modules.users.schemas import UserResponse
from app.schemas.common import StandardResponse
from app.api.deps import get_current_user
from app.modules.auth.service import AuthService
from app.models.user import User

router = APIRouter()

@router.post("/register", response_model=StandardResponse[TokenResponse], status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    token_response = await auth_service.register_user(payload)
    return StandardResponse.ok(data=token_response)

@router.post("/login", response_model=StandardResponse[TokenResponse])
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    token_response = await auth_service.authenticate_user(payload)
    return StandardResponse.ok(data=token_response)

@router.post("/refresh", response_model=StandardResponse[TokenResponse])
async def refresh_access_token(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    token_response = await auth_service.refresh_tokens(payload.refresh_token)
    return StandardResponse.ok(data=token_response)

@router.post("/logout", response_model=StandardResponse[dict])
async def logout(
    payload: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)
    await auth_service.logout(str(current_user.id), payload.refresh_token)
    return StandardResponse.ok(data={"message": "Logged out successfully."})

@router.get("/me", response_model=StandardResponse[UserResponse])
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return StandardResponse.ok(data=UserResponse.model_validate(current_user))
