from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_active_user
from app.models import db_models, schemas
from app.services import fixed_transaction_service, transaction_service

router = APIRouter(prefix="/fixed-transactions", tags=["fixed_transactions"])


def _get_fixed_tx(db: Session, fixed_tx_id: UUID, user_id: UUID) -> db_models.FixedTransaction:
    fixed_tx = db.query(db_models.FixedTransaction).filter(
        db_models.FixedTransaction.id == fixed_tx_id,
        db_models.FixedTransaction.user_id == user_id,
    ).first()
    if not fixed_tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fixed transaction not found")
    return fixed_tx


@router.post("", response_model=schemas.FixedTransactionResponse, status_code=status.HTTP_201_CREATED)
def create_fixed_transaction(
    payload: schemas.FixedTransactionCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    data = payload.model_dump()
    data["user_id"] = current_user.id
    fixed_tx = db_models.FixedTransaction(**data)
    db.add(fixed_tx)
    db.commit()
    db.refresh(fixed_tx)
    return fixed_tx


@router.get("", response_model=List[schemas.FixedTransactionResponse])
def list_fixed_transactions(
    status_filter: Optional[db_models.FixedTransactionStatus] = Query(None),
    transaction_type: Optional[db_models.TransactionType] = Query(None),
    currency: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    # Keep fixed tasks as monthly reminders by rolling old records into current month.
    fixed_transaction_service.roll_forward_monthly_fixed_transactions(db, current_user.id)

    query = db.query(db_models.FixedTransaction).filter(
        db_models.FixedTransaction.user_id == current_user.id
    )

    if status_filter:
        query = query.filter(db_models.FixedTransaction.status == status_filter)
    if transaction_type:
        query = query.filter(db_models.FixedTransaction.transaction_type == transaction_type)
    if currency:
        query = query.filter(db_models.FixedTransaction.currency == currency)
    if start_date:
        query = query.filter(db_models.FixedTransaction.estimated_date >= start_date)
    if end_date:
        query = query.filter(db_models.FixedTransaction.estimated_date <= end_date)

    return query.order_by(db_models.FixedTransaction.estimated_date.asc()).offset(skip).limit(limit).all()


@router.get("/{fixed_tx_id}", response_model=schemas.FixedTransactionResponse)
def get_fixed_transaction(
    fixed_tx_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    return _get_fixed_tx(db, fixed_tx_id, current_user.id)


@router.put("/{fixed_tx_id}", response_model=schemas.FixedTransactionResponse)
def update_fixed_transaction(
    fixed_tx_id: UUID,
    payload: schemas.FixedTransactionUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    fixed_tx = _get_fixed_tx(db, fixed_tx_id, current_user.id)
    if fixed_tx.status == db_models.FixedTransactionStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit completed fixed transaction")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(fixed_tx, field, value)
    db.commit()
    db.refresh(fixed_tx)
    return fixed_tx


@router.delete("/{fixed_tx_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fixed_transaction(
    fixed_tx_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    fixed_tx = _get_fixed_tx(db, fixed_tx_id, current_user.id)
    if fixed_tx.linked_transaction_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete completed fixed transaction")
    db.delete(fixed_tx)
    db.commit()
    return None


@router.post("/{fixed_tx_id}/omit", response_model=schemas.FixedTransactionResponse)
def omit_fixed_transaction(
    fixed_tx_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    fixed_tx = _get_fixed_tx(db, fixed_tx_id, current_user.id)
    if fixed_tx.status == db_models.FixedTransactionStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot omit a completed fixed transaction")
    fixed_tx.status = db_models.FixedTransactionStatus.SKIPPED
    db.commit()
    db.refresh(fixed_tx)
    return fixed_tx


@router.post("/{fixed_tx_id}/complete", response_model=schemas.FixedTransactionResponse)
def complete_fixed_transaction(
    fixed_tx_id: UUID,
    payload: schemas.FixedTransactionComplete,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    fixed_tx = _get_fixed_tx(db, fixed_tx_id, current_user.id)
    if fixed_tx.status == db_models.FixedTransactionStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fixed transaction already completed")

    tx_type = fixed_tx.transaction_type
    linked_transaction_id: Optional[UUID] = None

    if tx_type == db_models.TransactionType.INCOME:
        if not payload.destination_account_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Income requires destination account")
        created_tx = transaction_service.create_transaction(
            db,
            schemas.TransactionCreate(
                user_id=current_user.id,
                transaction_type=tx_type,
                amount=Decimal(payload.real_amount),
                currency=fixed_tx.currency,
                account_id=payload.destination_account_id,
                category_id=fixed_tx.category_id,
                transaction_date=payload.real_date,
                description=payload.description or fixed_tx.name,
                status=db_models.TransactionStatus.COMPLETED,
                source=db_models.TransactionSource.MANUAL,
            ),
        )
        linked_transaction_id = created_tx.id

    elif tx_type == db_models.TransactionType.EXPENSE:
        if not payload.source_account_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expense requires source account")
        created_tx = transaction_service.create_transaction(
            db,
            schemas.TransactionCreate(
                user_id=current_user.id,
                transaction_type=tx_type,
                amount=Decimal(payload.real_amount),
                currency=fixed_tx.currency,
                account_id=payload.source_account_id,
                category_id=fixed_tx.category_id,
                transaction_date=payload.real_date,
                description=payload.description or fixed_tx.name,
                status=db_models.TransactionStatus.COMPLETED,
                source=db_models.TransactionSource.MANUAL,
            ),
        )
        linked_transaction_id = created_tx.id

    elif tx_type == db_models.TransactionType.TRANSFER:
        if not payload.source_account_id or not payload.destination_account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transfer requires source and destination accounts",
            )
        source_tx, _dest_tx = transaction_service.create_transfer(
            db=db,
            user_id=current_user.id,
            from_account_id=payload.source_account_id,
            to_account_id=payload.destination_account_id,
            amount=Decimal(payload.real_amount),
            transaction_date=payload.real_date,
            description=payload.description or fixed_tx.name,
        )
        linked_transaction_id = source_tx.id
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported transaction type")

    fixed_tx.status = db_models.FixedTransactionStatus.COMPLETED
    fixed_tx.real_date = payload.real_date
    fixed_tx.real_amount = payload.real_amount
    fixed_tx.real_source_account_id = payload.source_account_id
    fixed_tx.real_destination_account_id = payload.destination_account_id
    fixed_tx.completion_notes = payload.description
    fixed_tx.linked_transaction_id = linked_transaction_id

    db.commit()
    db.refresh(fixed_tx)
    return fixed_tx


@router.post("/{fixed_tx_id}/reopen", response_model=schemas.FixedTransactionResponse)
def reopen_fixed_transaction(
    fixed_tx_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    fixed_tx = _get_fixed_tx(db, fixed_tx_id, current_user.id)

    if fixed_tx.linked_transaction_id:
        linked_tx = db.query(db_models.Transaction).filter(
            db_models.Transaction.id == fixed_tx.linked_transaction_id,
            db_models.Transaction.user_id == current_user.id,
        ).first()

        if linked_tx and linked_tx.status != db_models.TransactionStatus.CANCELLED:
            linked_tx.status = db_models.TransactionStatus.CANCELLED
            transaction_service.update_account_balance(db, linked_tx.account_id)

            if linked_tx.transaction_type == db_models.TransactionType.TRANSFER:
                mirror_tx = db.query(db_models.Transaction).filter(
                    db_models.Transaction.user_id == current_user.id,
                    db_models.Transaction.transaction_type == db_models.TransactionType.TRANSFER,
                    db_models.Transaction.account_id == linked_tx.counterparty_account_id,
                    db_models.Transaction.counterparty_account_id == linked_tx.account_id,
                    db_models.Transaction.amount == linked_tx.amount,
                    db_models.Transaction.transaction_date == linked_tx.transaction_date,
                    db_models.Transaction.status != db_models.TransactionStatus.CANCELLED,
                ).first()
                if mirror_tx:
                    mirror_tx.status = db_models.TransactionStatus.CANCELLED
                    transaction_service.update_account_balance(db, mirror_tx.account_id)

    fixed_tx.status = db_models.FixedTransactionStatus.PENDING
    fixed_tx.linked_transaction_id = None
    fixed_tx.real_date = None
    fixed_tx.real_amount = None
    fixed_tx.real_source_account_id = None
    fixed_tx.real_destination_account_id = None
    fixed_tx.completion_notes = None

    db.commit()
    db.refresh(fixed_tx)
    return fixed_tx
