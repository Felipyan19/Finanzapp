from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.api.dependencies import get_db, get_current_active_user
from app.models import db_models, schemas
from app.services import budget_service

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post("", response_model=schemas.BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget: schemas.BudgetCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Create a new budget."""
    category = db.query(db_models.Category).filter(
        db_models.Category.id == budget.category_id,
        db_models.Category.user_id == current_user.id,
    ).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if budget.end_date <= budget.start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End date must be after start date")

    budget_data = budget.model_dump()
    budget_data["user_id"] = current_user.id

    db_budget = db_models.Budget(**budget_data)
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget


@router.get("", response_model=List[schemas.BudgetResponse])
def list_budgets(
    category_id: Optional[UUID] = None,
    period_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """List budgets for the authenticated user."""
    query = db.query(db_models.Budget).filter(db_models.Budget.user_id == current_user.id)

    if category_id:
        query = query.filter(db_models.Budget.category_id == category_id)
    if period_type:
        query = query.filter(db_models.Budget.period_type == period_type)
    if is_active is not None:
        query = query.filter(db_models.Budget.is_active == is_active)

    return query.offset(skip).limit(limit).all()


@router.get("/{budget_id}", response_model=schemas.BudgetResponse)
def get_budget(
    budget_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get a budget by ID."""
    db_budget = db.query(db_models.Budget).filter(
        db_models.Budget.id == budget_id,
        db_models.Budget.user_id == current_user.id,
    ).first()
    if not db_budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return db_budget


@router.put("/{budget_id}", response_model=schemas.BudgetResponse)
def update_budget(
    budget_id: UUID,
    budget_update: schemas.BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Update a budget."""
    db_budget = db.query(db_models.Budget).filter(
        db_models.Budget.id == budget_id,
        db_models.Budget.user_id == current_user.id,
    ).first()
    if not db_budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    update_data = budget_update.model_dump(exclude_unset=True)
    if "start_date" in update_data or "end_date" in update_data:
        start = update_data.get("start_date", db_budget.start_date)
        end = update_data.get("end_date", db_budget.end_date)
        if end <= start:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End date must be after start date")

    for field, value in update_data.items():
        setattr(db_budget, field, value)

    db.commit()
    db.refresh(db_budget)
    return db_budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Delete a budget."""
    db_budget = db.query(db_models.Budget).filter(
        db_models.Budget.id == budget_id,
        db_models.Budget.user_id == current_user.id,
    ).first()
    if not db_budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    db.delete(db_budget)
    db.commit()
    return None


@router.get("/{budget_id}/progress", response_model=schemas.BudgetProgress)
def get_budget_progress(
    budget_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get budget progress including spent amount and percentage."""
    try:
        return budget_service.get_budget_progress(db, budget_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
