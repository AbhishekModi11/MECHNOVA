from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.models import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user with company credentials and enforce tab role verification."""
    user = db.query(User).filter(User.company_email == request.email.lower().strip()).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: No account associated with this email"
        )
    
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: Password incorrect"
        )
        
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Please contact your shop administrator."
        )

    # Strictly enforce login tab role match
    if user.role != request.role_tab:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Role Mismatch: Account '{user.company_email}' is registered as '{user.role.upper()}'. "
                f"Please switch to the '{user.role.title()} Login' tab."
            )
        )

    # Generate token
    token = create_access_token(data={"sub": user.company_email, "role": user.role, "uid": user.id})
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )
