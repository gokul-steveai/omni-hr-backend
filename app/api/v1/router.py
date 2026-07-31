from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.roles.router import permissions_router
from app.modules.roles.router import router as roles_router
from app.modules.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users & Profiles"])
api_router.include_router(roles_router)
api_router.include_router(permissions_router)
