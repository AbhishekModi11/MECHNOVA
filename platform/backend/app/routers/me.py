from fastapi import APIRouter, Depends
from app.deps import get_current_user, require_admin
from app.models.models import User
from app.schemas.auth import UserOut

router = APIRouter(prefix="/me", tags=["Current User"])


@router.get("", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve profile of the currently authenticated user."""
    return UserOut.model_validate(current_user)


@router.get("/admin-check")
def admin_only_check(admin_user: User = Depends(require_admin)):
    """Internal verification route to assert admin role enforcement."""
    return {"message": "Admin authorized", "admin_id": admin_user.company_id}
