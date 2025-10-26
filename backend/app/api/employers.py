from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.schemas.employer import EmployerCreate, EmployerResponse
from app.schemas.auth import Token
from app.models.employer import Employer
from app.utils.auth import get_password_hash, create_access_token, get_current_employer
from app.services.autonomous_agents.integration import autonomous_agent_integration

router = APIRouter(prefix="/employers", tags=["Employers"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_employer(
    employer_data: EmployerCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new employer
    Returns JWT access token
    """
    # Check if email already exists
    result = await db.execute(
        select(Employer).where(Employer.email == employer_data.email)
    )
    existing_employer = result.scalar_one_or_none()
    
    if existing_employer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new employer
    new_employer = Employer(
        company_name=employer_data.company_name,
        email=employer_data.email,
        password_hash=get_password_hash(employer_data.password)
    )
    
    db.add(new_employer)
    await db.commit()
    await db.refresh(new_employer)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(new_employer.id), "email": new_employer.email}
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=EmployerResponse)
async def get_current_employer_info(
    current_employer: Employer = Depends(get_current_employer)
):
    """Get current employer information"""
    return current_employer


@router.get("/{employer_id}/insights")
async def get_employer_insights(
    employer_id: str,
    vacancy_id: str,
    insights_type: str = "comprehensive",
    current_employer: Employer = Depends(get_current_employer)
):
    """Get insights and analysis for employer"""
    try:
        # Verify employer access
        if str(current_employer.id) != employer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get insights from autonomous agents
        insights_result = await autonomous_agent_integration.get_employer_insights(
            employer_id=employer_id,
            vacancy_id=vacancy_id,
            insights_type=insights_type
        )
        
        if insights_result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=insights_result["error"]
            )
        
        return insights_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{employer_id}/view-candidate")
async def view_candidate(
    employer_id: str,
    candidate_id: str,
    vacancy_id: str,
    current_employer: Employer = Depends(get_current_employer)
):
    """Record employer viewing a candidate (triggers autonomous analysis)"""
    try:
        # Verify employer access
        if str(current_employer.id) != employer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Integrate with autonomous agents
        integration_result = await autonomous_agent_integration.integrate_employer_view(
            employer_id=employer_id,
            candidate_id=candidate_id,
            vacancy_id=vacancy_id,
            db=None  # Will be handled internally
        )
        
        if integration_result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=integration_result["error"]
            )
        
        return {
            "success": True,
            "message": "Candidate view recorded and analysis initiated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

