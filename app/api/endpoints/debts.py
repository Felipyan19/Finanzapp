from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from app.api.dependencies import get_db, get_current_active_user
from app.models import db_models, schemas

router = APIRouter(prefix="/debts", tags=["debts"])


@router.post("", response_model=schemas.DebtResponse, status_code=status.HTTP_201_CREATED)
def create_debt(
    debt: schemas.DebtCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Create a new debt."""
    debt_data = debt.model_dump()
    debt_data["user_id"] = current_user.id
    debt_data["current_balance"] = debt_data["principal_amount"]

    db_debt = db_models.Debt(**debt_data)
    db.add(db_debt)
    db.commit()
    db.refresh(db_debt)
    return db_debt


@router.get("", response_model=List[schemas.DebtResponse])
def list_debts(
    debt_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """List debts for the authenticated user."""
    query = db.query(db_models.Debt).filter(db_models.Debt.user_id == current_user.id)

    if debt_type:
        query = query.filter(db_models.Debt.debt_type == debt_type)
    if status_filter:
        query = query.filter(db_models.Debt.status == status_filter)

    return query.order_by(db_models.Debt.due_date.asc().nullslast()).offset(skip).limit(limit).all()


@router.get("/{debt_id}", response_model=schemas.DebtResponse)
def get_debt(
    debt_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get a debt by ID."""
    db_debt = db.query(db_models.Debt).filter(
        db_models.Debt.id == debt_id,
        db_models.Debt.user_id == current_user.id,
    ).first()
    if not db_debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")
    return db_debt


@router.put("/{debt_id}", response_model=schemas.DebtResponse)
def update_debt(
    debt_id: UUID,
    debt_update: schemas.DebtUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Update a debt."""
    db_debt = db.query(db_models.Debt).filter(
        db_models.Debt.id == debt_id,
        db_models.Debt.user_id == current_user.id,
    ).first()
    if not db_debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")

    for field, value in debt_update.model_dump(exclude_unset=True).items():
        setattr(db_debt, field, value)

    db.commit()
    db.refresh(db_debt)
    return db_debt


@router.delete("/{debt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_debt(
    debt_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Cancel a debt."""
    db_debt = db.query(db_models.Debt).filter(
        db_models.Debt.id == debt_id,
        db_models.Debt.user_id == current_user.id,
    ).first()
    if not db_debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")

    db_debt.status = db_models.DebtStatus.CANCELLED
    db.commit()
    return None


@router.post("/{debt_id}/payments", response_model=schemas.DebtPaymentResponse, status_code=status.HTTP_201_CREATED)
def create_debt_payment(
    debt_id: UUID,
    payment: schemas.DebtPaymentCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Register a payment for a debt."""
    db_debt = db.query(db_models.Debt).filter(
        db_models.Debt.id == debt_id,
        db_models.Debt.user_id == current_user.id,
    ).first()
    if not db_debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")

    if db_debt.status != db_models.DebtStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot add payment to inactive debt")

    if payment.payment_amount != (payment.principal_component + payment.interest_component):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount must equal principal + interest components",
        )

    if payment.transaction_id:
        transaction = db.query(db_models.Transaction).filter(
            db_models.Transaction.id == payment.transaction_id,
            db_models.Transaction.user_id == current_user.id,
        ).first()
        if not transaction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    payment_data = payment.model_dump()
    payment_data["debt_id"] = debt_id
    db_payment = db_models.DebtPayment(**payment_data)
    db.add(db_payment)

    db_debt.current_balance -= payment.principal_component
    if db_debt.current_balance <= 0:
        db_debt.current_balance = Decimal("0")
        db_debt.status = db_models.DebtStatus.PAID

    db.commit()
    db.refresh(db_payment)
    return db_payment


@router.get("/{debt_id}/payments", response_model=List[schemas.DebtPaymentResponse])
def list_debt_payments(
    debt_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """List all payments for a debt."""
    db_debt = db.query(db_models.Debt).filter(
        db_models.Debt.id == debt_id,
        db_models.Debt.user_id == current_user.id,
    ).first()
    if not db_debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")

    return (
        db.query(db_models.DebtPayment)
        .filter(db_models.DebtPayment.debt_id == debt_id)
        .order_by(db_models.DebtPayment.payment_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
