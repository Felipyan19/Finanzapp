from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.api.dependencies import get_db
from app.models import db_models, schemas
from app.services import goal_service

router = APIRouter(prefix="/goals", tags=["financial_goals"])


@router.post("", response_model=schemas.FinancialGoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(goal: schemas.FinancialGoalCreate, db: Session = Depends(get_db)):
    """Create a new financial goal"""
    # Verify user exists
    user = db.query(db_models.User).filter(db_models.User.id == goal.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify account if provided
    if goal.account_id:
        account = db.query(db_models.Account).filter(db_models.Account.id == goal.account_id).first()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        if account.user_id != goal.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account does not belong to user"
            )

    db_goal = db_models.FinancialGoal(**goal.model_dump())
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal


@router.get("/{goal_id}", response_model=schemas.FinancialGoalResponse)
def get_goal(goal_id: UUID, db: Session = Depends(get_db)):
    """Get a financial goal by ID"""
    db_goal = db.query(db_models.FinancialGoal).filter(db_models.FinancialGoal.id == goal_id).first()
    if not db_goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )
    return db_goal


@router.get("", response_model=List[schemas.FinancialGoalResponse])
def list_goals(
    user_id: UUID = Query(...),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List financial goals with filters"""
    query = db.query(db_models.FinancialGoal).filter(db_models.FinancialGoal.user_id == user_id)

    if status_filter:
        query = query.filter(db_models.FinancialGoal.status == status_filter)

    query = query.order_by(db_models.FinancialGoal.priority.asc())
    goals = query.offset(skip).limit(limit).all()
    return goals


@router.put("/{goal_id}", response_model=schemas.FinancialGoalResponse)
def update_goal(
    goal_id: UUID,
    goal_update: schemas.FinancialGoalUpdate,
    db: Session = Depends(get_db)
):
    """Update a financial goal"""
    db_goal = db.query(db_models.FinancialGoal).filter(db_models.FinancialGoal.id == goal_id).first()
    if not db_goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )

    update_data = goal_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_goal, field, value)

    db.commit()
    db.refresh(db_goal)
    return db_goal


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: UUID, db: Session = Depends(get_db)):
    """Cancel a financial goal"""
    db_goal = db.query(db_models.FinancialGoal).filter(db_models.FinancialGoal.id == goal_id).first()
    if not db_goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )

    db_goal.status = db_models.GoalStatus.CANCELLED
    db.commit()
    return None


@router.post("/{goal_id}/contribute", response_model=schemas.FinancialGoalResponse)
def contribute_to_goal(
    goal_id: UUID,
    contribution: schemas.GoalContribution,
    db: Session = Depends(get_db)
):
    """Add a contribution to a financial goal"""
    try:
        updated_goal = goal_service.contribute_to_goal(db, goal_id, contribution.amount)
        return updated_goal
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{goal_id}/progress", response_model=schemas.GoalProgress)
def get_goal_progress(goal_id: UUID, db: Session = Depends(get_db)):
    """Get detailed progress for a financial goal"""
    try:
        return goal_service.calculate_progress(db, goal_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
