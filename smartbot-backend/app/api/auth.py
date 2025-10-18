from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.schemas.auth import Token
from app.schemas.employer import EmployerLogin
from app.models.employer import Employer
from app.utils.auth import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(
    credentials: EmployerLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Login endpoint for employers
    Returns JWT access token
    """
    # Find employer by email
    result = await db.execute(
        select(Employer).where(Employer.email == credentials.email)
    )
    employer = result.scalar_one_or_none()
    
    # Verify credentials
    if not employer or not verify_password(credentials.password, employer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(employer.id), "email": employer.email}
    )
    
    return Token(access_token=access_token, token_type="bearer")

