from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.api.dependencies import get_db, get_current_active_user
from app.models import db_models, schemas
from app.services import goal_service

router = APIRouter(prefix="/goals", tags=["financial_goals"])


@router.post("", response_model=schemas.FinancialGoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    goal: schemas.FinancialGoalCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Create a new financial goal."""
    if goal.account_id:
        account = db.query(db_models.Account).filter(
            db_models.Account.id == goal.account_id,
            db_models.Account.user_id == current_user.id,
        ).first()
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    goal_data = goal.model_dump()
    goal_data["user_id"] = current_user.id

    db_goal = db_models.FinancialGoal(**goal_data)
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal


@router.get("", response_model=List[schemas.FinancialGoalResponse])
def list_goals(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """List financial goals for the authenticated user."""
    query = db.query(db_models.FinancialGoal).filter(
        db_models.FinancialGoal.user_id == current_user.id
    )
    if status_filter:
        query = query.filter(db_models.FinancialGoal.status == status_filter)

    return query.order_by(db_models.FinancialGoal.priority.asc()).offset(skip).limit(limit).all()


@router.get("/{goal_id}", response_model=schemas.FinancialGoalResponse)
def get_goal(
    goal_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get a financial goal by ID."""
    db_goal = db.query(db_models.FinancialGoal).filter(
        db_models.FinancialGoal.id == goal_id,
        db_models.FinancialGoal.user_id == current_user.id,
    ).first()
    if not db_goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return db_goal


@router.put("/{goal_id}", response_model=schemas.FinancialGoalResponse)
def update_goal(
    goal_id: UUID,
    goal_update: schemas.FinancialGoalUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Update a financial goal."""
    db_goal = db.query(db_models.FinancialGoal).filter(
        db_models.FinancialGoal.id == goal_id,
        db_models.FinancialGoal.user_id == current_user.id,
    ).first()
    if not db_goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    for field, value in goal_update.model_dump(exclude_unset=True).items():
        setattr(db_goal, field, value)

    db.commit()
    db.refresh(db_goal)
    return db_goal


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Cancel a financial goal."""
    db_goal = db.query(db_models.FinancialGoal).filter(
        db_models.FinancialGoal.id == goal_id,
        db_models.FinancialGoal.user_id == current_user.id,
    ).first()
    if not db_goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    db_goal.status = db_models.GoalStatus.CANCELLED
    db.commit()
    return None


@router.post("/{goal_id}/contribute", response_model=schemas.FinancialGoalResponse)
def contribute_to_goal(
    goal_id: UUID,
    contribution: schemas.GoalContribution,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Add a contribution to a financial goal."""
    db_goal = db.query(db_models.FinancialGoal).filter(
        db_models.FinancialGoal.id == goal_id,
        db_models.FinancialGoal.user_id == current_user.id,
    ).first()
    if not db_goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    try:
        return goal_service.contribute_to_goal(db, goal_id, contribution.amount)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{goal_id}/progress", response_model=schemas.GoalProgress)
def get_goal_progress(
    goal_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get detailed progress for a financial goal."""
    db_goal = db.query(db_models.FinancialGoal).filter(
        db_models.FinancialGoal.id == goal_id,
        db_models.FinancialGoal.user_id == current_user.id,
    ).first()
    if not db_goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    try:
        return goal_service.calculate_progress(db, goal_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
