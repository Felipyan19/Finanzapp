from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta
from uuid import UUID

from app.api.dependencies import get_db, get_current_active_user
from app.models import db_models, schemas
from app.services import transaction_service

router = APIRouter(prefix="/recurring", tags=["recurring_transactions"])


def calculate_next_execution_date(start_date: date, frequency: str) -> date:
    if frequency == "daily":
        return start_date + timedelta(days=1)
    elif frequency == "weekly":
        return start_date + timedelta(weeks=1)
    elif frequency == "biweekly":
        return start_date + timedelta(weeks=2)
    elif frequency == "monthly":
        month = start_date.month + 1
        year = start_date.year
        if month > 12:
            month = 1
            year += 1
        try:
            return date(year, month, start_date.day)
        except ValueError:
            return date(year, month, 28)
    elif frequency == "quarterly":
        month = start_date.month + 3
        year = start_date.year
        while month > 12:
            month -= 12
            year += 1
        try:
            return date(year, month, start_date.day)
        except ValueError:
            return date(year, month, 28)
    elif frequency == "yearly":
        return date(start_date.year + 1, start_date.month, start_date.day)
    return start_date


@router.post("", response_model=schemas.RecurringTransactionResponse, status_code=status.HTTP_201_CREATED)
def create_recurring_transaction(
    recurring: schemas.RecurringTransactionCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Create a new recurring transaction."""
    account = db.query(db_models.Account).filter(
        db_models.Account.id == recurring.account_id,
        db_models.Account.user_id == current_user.id,
    ).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    if recurring.category_id:
        category = db.query(db_models.Category).filter(
            db_models.Category.id == recurring.category_id,
            db_models.Category.user_id == current_user.id,
        ).first()
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    recurring_data = recurring.model_dump()
    recurring_data["user_id"] = current_user.id
    recurring_data["next_execution_date"] = calculate_next_execution_date(
        recurring.start_date, recurring.frequency.value
    )

    db_recurring = db_models.RecurringTransaction(**recurring_data)
    db.add(db_recurring)
    db.commit()
    db.refresh(db_recurring)
    return db_recurring


@router.get("", response_model=List[schemas.RecurringTransactionResponse])
def list_recurring_transactions(
    is_active: Optional[bool] = None,
    frequency: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """List recurring transactions for the authenticated user."""
    query = db.query(db_models.RecurringTransaction).filter(
        db_models.RecurringTransaction.user_id == current_user.id
    )

    if is_active is not None:
        query = query.filter(db_models.RecurringTransaction.is_active == is_active)
    if frequency:
        query = query.filter(db_models.RecurringTransaction.frequency == frequency)

    return query.order_by(db_models.RecurringTransaction.next_execution_date.asc()).offset(skip).limit(limit).all()


@router.get("/{recurring_id}", response_model=schemas.RecurringTransactionResponse)
def get_recurring_transaction(
    recurring_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get a recurring transaction by ID."""
    db_recurring = db.query(db_models.RecurringTransaction).filter(
        db_models.RecurringTransaction.id == recurring_id,
        db_models.RecurringTransaction.user_id == current_user.id,
    ).first()
    if not db_recurring:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring transaction not found")
    return db_recurring


@router.put("/{recurring_id}", response_model=schemas.RecurringTransactionResponse)
def update_recurring_transaction(
    recurring_id: UUID,
    recurring_update: schemas.RecurringTransactionUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Update a recurring transaction."""
    db_recurring = db.query(db_models.RecurringTransaction).filter(
        db_models.RecurringTransaction.id == recurring_id,
        db_models.RecurringTransaction.user_id == current_user.id,
    ).first()
    if not db_recurring:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring transaction not found")

    update_data = recurring_update.model_dump(exclude_unset=True)
    if "frequency" in update_data:
        update_data["next_execution_date"] = calculate_next_execution_date(
            db_recurring.next_execution_date, update_data["frequency"].value
        )

    for field, value in update_data.items():
        setattr(db_recurring, field, value)

    db.commit()
    db.refresh(db_recurring)
    return db_recurring


@router.delete("/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_transaction(
    recurring_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Deactivate a recurring transaction."""
    db_recurring = db.query(db_models.RecurringTransaction).filter(
        db_models.RecurringTransaction.id == recurring_id,
        db_models.RecurringTransaction.user_id == current_user.id,
    ).first()
    if not db_recurring:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring transaction not found")

    db_recurring.is_active = False
    db.commit()
    return None


@router.post("/{recurring_id}/execute", response_model=schemas.TransactionResponse)
def execute_recurring_transaction(
    recurring_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Manually execute a recurring transaction."""
    db_recurring = db.query(db_models.RecurringTransaction).filter(
        db_models.RecurringTransaction.id == recurring_id,
        db_models.RecurringTransaction.user_id == current_user.id,
    ).first()
    if not db_recurring:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring transaction not found")

    if not db_recurring.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot execute inactive recurring transaction")

    transaction = schemas.TransactionCreate(
        user_id=current_user.id,
        transaction_type=db_recurring.transaction_type,
        amount=db_recurring.amount,
        account_id=db_recurring.account_id,
        category_id=db_recurring.category_id,
        transaction_date=date.today(),
        description=f"Recurring: {db_recurring.name}",
        status=db_models.TransactionStatus.COMPLETED,
        source=db_models.TransactionSource.RECURRING,
    )

    try:
        db_transaction = transaction_service.create_transaction(db, transaction)
        db_recurring.next_execution_date = calculate_next_execution_date(
            db_recurring.next_execution_date, db_recurring.frequency.value
        )
        db.commit()
        return db_transaction
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
