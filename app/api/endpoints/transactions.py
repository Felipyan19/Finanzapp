from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.api.dependencies import get_db
from app.models import db_models, schemas
from app.services import transaction_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=schemas.TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    """Create a new transaction"""
    try:
        db_transaction = transaction_service.create_transaction(db, transaction)
        return db_transaction
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/transfer", status_code=status.HTTP_201_CREATED)
def create_transfer(
    user_id: UUID,
    from_account_id: UUID,
    to_account_id: UUID,
    amount: Decimal = Query(..., gt=0),
    transaction_date: date = Query(...),
    description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Create a transfer between accounts"""
    try:
        source_tx, dest_tx = transaction_service.create_transfer(
            db, user_id, from_account_id, to_account_id, amount, transaction_date, description
        )
        return {
            "source_transaction": schemas.TransactionResponse.model_validate(source_tx),
            "destination_transaction": schemas.TransactionResponse.model_validate(dest_tx)
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{transaction_id}", response_model=schemas.TransactionResponse)
def get_transaction(transaction_id: UUID, db: Session = Depends(get_db)):
    """Get a transaction by ID"""
    db_transaction = db.query(db_models.Transaction).filter(
        db_models.Transaction.id == transaction_id
    ).first()
    if not db_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    return db_transaction


@router.get("", response_model=List[schemas.TransactionResponse])
def list_transactions(
    user_id: UUID = Query(...),
    account_id: Optional[UUID] = None,
    category_id: Optional[UUID] = None,
    transaction_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List transactions with filters"""
    query = db.query(db_models.Transaction).filter(
        db_models.Transaction.user_id == user_id
    )

    if account_id:
        query = query.filter(db_models.Transaction.account_id == account_id)

    if category_id:
        query = query.filter(db_models.Transaction.category_id == category_id)

    if transaction_type:
        query = query.filter(db_models.Transaction.transaction_type == transaction_type)

    if status_filter:
        query = query.filter(db_models.Transaction.status == status_filter)

    if start_date:
        query = query.filter(db_models.Transaction.transaction_date >= start_date)

    if end_date:
        query = query.filter(db_models.Transaction.transaction_date <= end_date)

    query = query.order_by(db_models.Transaction.transaction_date.desc())
    transactions = query.offset(skip).limit(limit).all()
    return transactions


@router.put("/{transaction_id}", response_model=schemas.TransactionResponse)
def update_transaction(
    transaction_id: UUID,
    transaction_update: schemas.TransactionUpdate,
    db: Session = Depends(get_db)
):
    """Update a transaction"""
    db_transaction = db.query(db_models.Transaction).filter(
        db_models.Transaction.id == transaction_id
    ).first()
    if not db_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    # Store old amount and status for balance recalculation
    old_amount = db_transaction.amount
    old_status = db_transaction.status

    update_data = transaction_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_transaction, field, value)

    db.commit()
    db.refresh(db_transaction)

    # Recalculate balance if amount or status changed
    if ('amount' in update_data or 'status' in update_data) and db_transaction.status == db_models.TransactionStatus.COMPLETED:
        transaction_service.update_account_balance(db, db_transaction.account_id)

    return db_transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: UUID, db: Session = Depends(get_db)):
    """Cancel a transaction"""
    db_transaction = db.query(db_models.Transaction).filter(
        db_models.Transaction.id == transaction_id
    ).first()
    if not db_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    db_transaction.status = db_models.TransactionStatus.CANCELLED
    db.commit()

    # Recalculate account balance
    transaction_service.update_account_balance(db, db_transaction.account_id)

    return None


@router.get("/summary/period", response_model=schemas.TransactionSummary)
def get_transaction_summary(
    user_id: UUID = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    account_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """Get transaction summary for a period"""
    return transaction_service.get_summary(db, user_id, start_date, end_date, account_id)


@router.get("/by-category/summary", response_model=List[schemas.TransactionByCategory])
def get_transactions_by_category(
    user_id: UUID = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    transaction_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get transactions grouped by category"""
    return transaction_service.get_by_category(db, user_id, start_date, end_date, transaction_type)
