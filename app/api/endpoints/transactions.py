from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.api.dependencies import get_db, get_current_active_user
from app.models import db_models, schemas
from app.services import transaction_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=schemas.TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Create a new transaction for the authenticated user."""
    transaction_data = transaction.model_dump()
    transaction_data["user_id"] = current_user.id
    transaction_obj = schemas.TransactionCreate(**transaction_data)
    try:
        db_transaction = transaction_service.create_transaction(db, transaction_obj)
        return db_transaction
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/transfer", status_code=status.HTTP_201_CREATED)
def create_transfer(
    from_account_id: UUID,
    to_account_id: UUID,
    amount: Decimal = Query(..., gt=0),
    transaction_date: date = Query(...),
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Create a transfer between accounts of the authenticated user."""
    try:
        source_tx, dest_tx = transaction_service.create_transfer(
            db, current_user.id, from_account_id, to_account_id, amount, transaction_date, description
        )
        return {
            "source_transaction": schemas.TransactionResponse.model_validate(source_tx),
            "destination_transaction": schemas.TransactionResponse.model_validate(dest_tx),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[schemas.TransactionResponse])
def list_transactions(
    account_id: Optional[UUID] = None,
    category_id: Optional[UUID] = None,
    transaction_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """List transactions for the authenticated user."""
    query = db.query(db_models.Transaction).filter(
        db_models.Transaction.user_id == current_user.id
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
    return query.offset(skip).limit(limit).all()


@router.get("/summary/period", response_model=schemas.TransactionSummary)
def get_transaction_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    account_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get transaction summary for a period."""
    return transaction_service.get_summary(db, current_user.id, start_date, end_date, account_id)


@router.get("/by-category/summary", response_model=List[schemas.TransactionByCategory])
def get_transactions_by_category(
    start_date: date = Query(...),
    end_date: date = Query(...),
    transaction_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get transactions grouped by category."""
    return transaction_service.get_by_category(db, current_user.id, start_date, end_date, transaction_type)


@router.get("/{transaction_id}", response_model=schemas.TransactionResponse)
def get_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get a transaction by ID."""
    db_transaction = db.query(db_models.Transaction).filter(
        db_models.Transaction.id == transaction_id,
        db_models.Transaction.user_id == current_user.id,
    ).first()
    if not db_transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return db_transaction


@router.put("/{transaction_id}", response_model=schemas.TransactionResponse)
def update_transaction(
    transaction_id: UUID,
    transaction_update: schemas.TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Update a transaction."""
    db_transaction = db.query(db_models.Transaction).filter(
        db_models.Transaction.id == transaction_id,
        db_models.Transaction.user_id == current_user.id,
    ).first()
    if not db_transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    update_data = transaction_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_transaction, field, value)

    db.commit()
    db.refresh(db_transaction)

    if ("amount" in update_data or "status" in update_data) and db_transaction.status == db_models.TransactionStatus.COMPLETED:
        transaction_service.update_account_balance(db, db_transaction.account_id)

    return db_transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Cancel a transaction."""
    db_transaction = db.query(db_models.Transaction).filter(
        db_models.Transaction.id == transaction_id,
        db_models.Transaction.user_id == current_user.id,
    ).first()
    if not db_transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    db_transaction.status = db_models.TransactionStatus.CANCELLED
    db.commit()
    transaction_service.update_account_balance(db, db_transaction.account_id)
    return None
