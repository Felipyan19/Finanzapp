from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from decimal import Decimal
from datetime import date
from uuid import UUID

from app.models import db_models, schemas


def get_budget_progress(db: Session, budget_id: UUID) -> schemas.BudgetProgress:
    """
    Calculate budget progress including spent amount and percentage.
    """
    budget = db.query(db_models.Budget).filter(db_models.Budget.id == budget_id).first()
    if not budget:
        raise ValueError("Budget not found")

    # Get category info
    category = db.query(db_models.Category).filter(db_models.Category.id == budget.category_id).first()
    category_name = category.name if category else "Unknown"

    # Calculate spent amount in the budget period
    spent_amount = get_spending_by_period(
        db,
        budget.user_id,
        budget.category_id,
        budget.start_date,
        budget.end_date
    )

    # Calculate remaining and percentage
    remaining_amount = budget.amount - spent_amount
    percentage_used = (spent_amount / budget.amount * 100) if budget.amount > 0 else Decimal("0")
    is_exceeded = spent_amount > budget.amount

    return schemas.BudgetProgress(
        budget_id=budget.id,
        category_name=category_name,
        budget_amount=budget.amount,
        spent_amount=spent_amount,
        remaining_amount=remaining_amount,
        percentage_used=round(percentage_used, 2),
        is_exceeded=is_exceeded,
        period_start=budget.start_date,
        period_end=budget.end_date
    )


def check_budget_exceeded(db: Session, user_id: UUID, category_id: UUID, current_date: date) -> bool:
    """
    Check if any active budget for the category is exceeded.
    Returns True if budget is exceeded.
    """
    # Find active budgets for this category that include current date
    budgets = db.query(db_models.Budget).filter(
        db_models.Budget.user_id == user_id,
        db_models.Budget.category_id == category_id,
        db_models.Budget.is_active == True,
        db_models.Budget.start_date <= current_date,
        db_models.Budget.end_date >= current_date
    ).all()

    for budget in budgets:
        spent = get_spending_by_period(db, user_id, category_id, budget.start_date, budget.end_date)
        if spent > budget.amount:
            return True

    return False


def get_spending_by_period(
    db: Session,
    user_id: UUID,
    category_id: UUID,
    start_date: date,
    end_date: date
) -> Decimal:
    """
    Calculate total spending for a category in a given period.
    """
    result = db.query(
        func.coalesce(func.sum(db_models.Transaction.amount), 0)
    ).filter(
        db_models.Transaction.user_id == user_id,
        db_models.Transaction.category_id == category_id,
        db_models.Transaction.transaction_type == db_models.TransactionType.EXPENSE,
        db_models.Transaction.status == db_models.TransactionStatus.COMPLETED,
        db_models.Transaction.transaction_date >= start_date,
        db_models.Transaction.transaction_date <= end_date
    ).scalar()

    return Decimal(str(result)) if result else Decimal("0")
