from fastapi import APIRouter, Depends
from app.core.security import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def get_my_profile(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Return the identity of the authenticated user verified by Supabase token."""
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role,
        }
    }

