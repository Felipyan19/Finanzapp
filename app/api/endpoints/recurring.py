from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta
from uuid import UUID

from app.api.dependencies import get_db
from app.models import db_models, schemas
from app.services import transaction_service

router = APIRouter(prefix="/recurring", tags=["recurring_transactions"])


def calculate_next_execution_date(start_date: date, frequency: str) -> date:
    """Calculate the next execution date based on frequency"""
    if frequency == "daily":
        return start_date + timedelta(days=1)
    elif frequency == "weekly":
        return start_date + timedelta(weeks=1)
    elif frequency == "biweekly":
        return start_date + timedelta(weeks=2)
    elif frequency == "monthly":
        # Simple monthly calculation (same day next month)
        month = start_date.month + 1
        year = start_date.year
        if month > 12:
            month = 1
            year += 1
        try:
            return date(year, month, start_date.day)
        except ValueError:
            # Handle month-end edge cases
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
    else:
        return start_date


@router.post("", response_model=schemas.RecurringTransactionResponse, status_code=status.HTTP_201_CREATED)
def create_recurring_transaction(recurring: schemas.RecurringTransactionCreate, db: Session = Depends(get_db)):
    """Create a new recurring transaction"""
    # Verify user exists
    user = db.query(db_models.User).filter(db_models.User.id == recurring.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify account exists and belongs to user
    account = db.query(db_models.Account).filter(db_models.Account.id == recurring.account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    if account.user_id != recurring.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account does not belong to user"
        )

    # Verify category if provided
    if recurring.category_id:
        category = db.query(db_models.Category).filter(db_models.Category.id == recurring.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        if category.user_id != recurring.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category does not belong to user"
            )

    # Calculate next execution date
    recurring_data = recurring.model_dump()
    recurring_data['next_execution_date'] = calculate_next_execution_date(
        recurring.start_date,
        recurring.frequency.value
    )

    db_recurring = db_models.RecurringTransaction(**recurring_data)
    db.add(db_recurring)
    db.commit()
    db.refresh(db_recurring)
    return db_recurring


@router.get("/{recurring_id}", response_model=schemas.RecurringTransactionResponse)
def get_recurring_transaction(recurring_id: UUID, db: Session = Depends(get_db)):
    """Get a recurring transaction by ID"""
    db_recurring = db.query(db_models.RecurringTransaction).filter(
        db_models.RecurringTransaction.id == recurring_id
    ).first()
    if not db_recurring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring transaction not found"
        )
    return db_recurring


@router.get("", response_model=List[schemas.RecurringTransactionResponse])
def list_recurring_transactions(
    user_id: UUID = Query(...),
    is_active: Optional[bool] = None,
    frequency: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List recurring transactions with filters"""
    query = db.query(db_models.RecurringTransaction).filter(
        db_models.RecurringTransaction.user_id == user_id
    )

    if is_active is not None:
        query = query.filter(db_models.RecurringTransaction.is_active == is_active)

    if frequency:
        query = query.filter(db_models.RecurringTransaction.frequency == frequency)

    query = query.order_by(db_models.RecurringTransaction.next_execution_date.asc())
    recurring = query.offset(skip).limit(limit).all()
    return recurring


@router.put("/{recurring_id}", response_model=schemas.RecurringTransactionResponse)
def update_recurring_transaction(
    recurring_id: UUID,
    recurring_update: schemas.RecurringTransactionUpdate,
    db: Session = Depends(get_db)
):
    """Update a recurring transaction"""
    db_recurring = db.query(db_models.RecurringTransaction).filter(
        db_models.RecurringTransaction.id == recurring_id
    ).first()
    if not db_recurring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring transaction not found"
        )

    update_data = recurring_update.model_dump(exclude_unset=True)

    # Recalculate next execution date if frequency changed
    if 'frequency' in update_data:
        update_data['next_execution_date'] = calculate_next_execution_date(
            db_recurring.next_execution_date,
            update_data['frequency'].value
        )

    for field, value in update_data.items():
        setattr(db_recurring, field, value)

    db.commit()
    db.refresh(db_recurring)
    return db_recurring


@router.delete("/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_transaction(recurring_id: UUID, db: Session = Depends(get_db)):
    """Deactivate a recurring transaction"""
    db_recurring = db.query(db_models.RecurringTransaction).filter(
        db_models.RecurringTransaction.id == recurring_id
    ).first()
    if not db_recurring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring transaction not found"
        )

    db_recurring.is_active = False
    db.commit()
    return None


@router.post("/{recurring_id}/execute", response_model=schemas.TransactionResponse)
def execute_recurring_transaction(recurring_id: UUID, db: Session = Depends(get_db)):
    """Manually execute a recurring transaction"""
    db_recurring = db.query(db_models.RecurringTransaction).filter(
        db_models.RecurringTransaction.id == recurring_id
    ).first()
    if not db_recurring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring transaction not found"
        )

    if not db_recurring.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot execute inactive recurring transaction"
        )

    # Create transaction from recurring template
    transaction = schemas.TransactionCreate(
        user_id=db_recurring.user_id,
        transaction_type=db_recurring.transaction_type,
        amount=db_recurring.amount,
        account_id=db_recurring.account_id,
        category_id=db_recurring.category_id,
        transaction_date=date.today(),
        description=f"Recurring: {db_recurring.name}",
        status=db_models.TransactionStatus.COMPLETED,
        source=db_models.TransactionSource.RECURRING
    )

    try:
        db_transaction = transaction_service.create_transaction(db, transaction)

        # Update next execution date
        db_recurring.next_execution_date = calculate_next_execution_date(
            db_recurring.next_execution_date,
            db_recurring.frequency.value
        )
        db.commit()

        return db_transaction
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
