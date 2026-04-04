from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from app.models import db_models, schemas


def contribute_to_goal(db: Session, goal_id: UUID, amount: Decimal) -> db_models.FinancialGoal:
    """
    Add a contribution to a financial goal.
    Updates current_amount and status if goal is completed.
    """
    goal = db.query(db_models.FinancialGoal).filter(db_models.FinancialGoal.id == goal_id).first()
    if not goal:
        raise ValueError("Goal not found")

    if goal.status != db_models.GoalStatus.ACTIVE:
        raise ValueError("Cannot contribute to inactive or completed goal")

    if amount <= 0:
        raise ValueError("Contribution amount must be positive")

    # Update current amount
    goal.current_amount += amount

    # Check if goal is now completed
    if goal.current_amount >= goal.target_amount:
        goal.status = db_models.GoalStatus.COMPLETED

    db.commit()
    db.refresh(goal)

    return goal


def calculate_progress(db: Session, goal_id: UUID) -> schemas.GoalProgress:
    """
    Calculate detailed progress for a financial goal.
    """
    goal = db.query(db_models.FinancialGoal).filter(db_models.FinancialGoal.id == goal_id).first()
    if not goal:
        raise ValueError("Goal not found")

    remaining_amount = goal.target_amount - goal.current_amount
    percentage_complete = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else Decimal("0")
    is_completed = goal.current_amount >= goal.target_amount

    # Estimate completion date
    estimated_completion = estimate_completion_date(db, goal_id)

    return schemas.GoalProgress(
        goal_id=goal.id,
        goal_name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        remaining_amount=max(remaining_amount, Decimal("0")),
        percentage_complete=round(percentage_complete, 2),
        is_completed=is_completed,
        target_date=goal.target_date,
        estimated_completion_date=estimated_completion
    )


def estimate_completion_date(db: Session, goal_id: UUID) -> Optional[date]:
    """
    Estimate when the goal will be completed based on contribution history.
    Returns None if cannot estimate or goal is already completed.
    """
    goal = db.query(db_models.FinancialGoal).filter(db_models.FinancialGoal.id == goal_id).first()
    if not goal:
        return None

    # If already completed
    if goal.current_amount >= goal.target_amount:
        return date.today()

    # If no progress yet
    if goal.current_amount == 0:
        return None

    # Calculate days since goal creation
    days_elapsed = (date.today() - goal.created_at.date()).days
    if days_elapsed <= 0:
        return None

    # Calculate average daily contribution
    avg_daily_contribution = goal.current_amount / days_elapsed

    if avg_daily_contribution <= 0:
        return None

    # Calculate remaining amount needed
    remaining = goal.target_amount - goal.current_amount

    # Estimate days needed
    days_needed = int(remaining / avg_daily_contribution)

    # Calculate estimated completion date
    estimated_date = date.today() + timedelta(days=days_needed)

    return estimated_date
