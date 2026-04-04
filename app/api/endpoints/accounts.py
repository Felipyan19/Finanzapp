from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.api.dependencies import get_db
from app.models import db_models, schemas

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=schemas.AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db)):
    """Create a new account"""
    # Verify user exists
    user = db.query(db_models.User).filter(db_models.User.id == account.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Create account with current_balance = initial_balance
    account_data = account.model_dump()
    account_data['current_balance'] = account_data['initial_balance']

    db_account = db_models.Account(**account_data)
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account


@router.get("/{account_id}", response_model=schemas.AccountResponse)
def get_account(account_id: UUID, db: Session = Depends(get_db)):
    """Get an account by ID"""
    db_account = db.query(db_models.Account).filter(db_models.Account.id == account_id).first()
    if not db_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    return db_account


@router.get("", response_model=List[schemas.AccountResponse])
def list_accounts(
    user_id: UUID = None,
    account_type: str = None,
    is_active: bool = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List accounts with optional filters"""
    query = db.query(db_models.Account)

    if user_id:
        query = query.filter(db_models.Account.user_id == user_id)

    if account_type:
        query = query.filter(db_models.Account.account_type == account_type)

    if is_active is not None:
        query = query.filter(db_models.Account.is_active == is_active)

    accounts = query.offset(skip).limit(limit).all()
    return accounts


@router.put("/{account_id}", response_model=schemas.AccountResponse)
def update_account(
    account_id: UUID,
    account_update: schemas.AccountUpdate,
    db: Session = Depends(get_db)
):
    """Update an account"""
    db_account = db.query(db_models.Account).filter(db_models.Account.id == account_id).first()
    if not db_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    update_data = account_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_account, field, value)

    db.commit()
    db.refresh(db_account)
    return db_account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: UUID, db: Session = Depends(get_db)):
    """Deactivate an account (soft delete)"""
    db_account = db.query(db_models.Account).filter(db_models.Account.id == account_id).first()
    if not db_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    db_account.is_active = False
    db.commit()
    return None


@router.get("/{account_id}/balance", response_model=schemas.AccountBalanceResponse)
def get_account_balance(account_id: UUID, db: Session = Depends(get_db)):
    """Get current account balance"""
    db_account = db.query(db_models.Account).filter(db_models.Account.id == account_id).first()
    if not db_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    return schemas.AccountBalanceResponse(
        account_id=db_account.id,
        account_name=db_account.name,
        current_balance=db_account.current_balance,
        currency=db_account.currency
    )
