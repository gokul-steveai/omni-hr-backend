from pydantic import BaseModel, EmailStr
from app.models.user import UserRole

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: UserRole = UserRole.EMPLOYEE

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int

class RefreshTokenRequest(BaseModel):
    refresh_token: str
