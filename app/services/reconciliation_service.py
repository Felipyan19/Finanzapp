"""
Reconciliation Service
Handles bank reconciliation logic
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from app.models import db_models, schemas


def create_reconciliation(
    db: Session,
    reconciliation: schemas.ReconciliationCreate,
    user_id: UUID
) -> db_models.Reconciliation:
    """
    Create a new reconciliation record

    Steps:
    1. Verify account exists and belongs to user
    2. Calculate system balance from account
    3. Calculate difference
    4. Set status based on difference
    """
    # Verify account exists and belongs to user
    account = db.query(db_models.Account).filter(
        db_models.Account.id == reconciliation.account_id,
        db_models.Account.user_id == user_id
    ).first()

    if not account:
        raise ValueError("Account not found or does not belong to user")

    # Get system balance
    system_balance = account.current_balance

    # Create reconciliation record
    db_reconciliation = db_models.Reconciliation(
        account_id=reconciliation.account_id,
        reconciliation_date=reconciliation.reconciliation_date,
        statement_balance=reconciliation.statement_balance,
        system_balance=system_balance,
        difference=Decimal("0"),  # Will be calculated
        notes=reconciliation.notes
    )

    # Calculate difference and set status
    db_reconciliation.calculate_difference()

    db.add(db_reconciliation)
    db.commit()
    db.refresh(db_reconciliation)

    return db_reconciliation


def get_reconciliation_by_id(
    db: Session,
    reconciliation_id: UUID,
    user_id: UUID
) -> Optional[db_models.Reconciliation]:
    """Get a reconciliation by ID (verify it belongs to user's account)"""
    return db.query(db_models.Reconciliation).join(
        db_models.Account
    ).filter(
        db_models.Reconciliation.id == reconciliation_id,
        db_models.Account.user_id == user_id
    ).first()


def get_reconciliations(
    db: Session,
    user_id: UUID,
    account_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[db_models.ReconciliationStatus] = None,
    skip: int = 0,
    limit: int = 100
) -> List[db_models.Reconciliation]:
    """
    Get reconciliations for a user with filters
    """
    query = db.query(db_models.Reconciliation).join(
        db_models.Account
    ).filter(
        db_models.Account.user_id == user_id
    )

    if account_id:
        query = query.filter(db_models.Reconciliation.account_id == account_id)

    if start_date:
        query = query.filter(db_models.Reconciliation.reconciliation_date >= start_date)

    if end_date:
        query = query.filter(db_models.Reconciliation.reconciliation_date <= end_date)

    if status:
        query = query.filter(db_models.Reconciliation.status == status)

    query = query.order_by(db_models.Reconciliation.reconciliation_date.desc())
    query = query.offset(skip).limit(limit)

    return query.all()


def update_reconciliation(
    db: Session,
    reconciliation_id: UUID,
    user_id: UUID,
    update_data: schemas.ReconciliationUpdate
) -> db_models.Reconciliation:
    """Update a reconciliation record"""
    db_reconciliation = get_reconciliation_by_id(db, reconciliation_id, user_id)

    if not db_reconciliation:
        raise ValueError("Reconciliation not found")

    # Don't allow updates to reconciled records
    if db_reconciliation.status == db_models.ReconciliationStatus.RECONCILED:
        raise ValueError("Cannot update a reconciled record")

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)

    for field, value in update_dict.items():
        if field != 'statement_balance':
            setattr(db_reconciliation, field, value)

    # If statement balance changed, recalculate
    if 'statement_balance' in update_dict:
        db_reconciliation.statement_balance = update_dict['statement_balance']
        db_reconciliation.calculate_difference()

    db.commit()
    db.refresh(db_reconciliation)

    return db_reconciliation


def complete_reconciliation(
    db: Session,
    reconciliation_id: UUID,
    user_id: UUID,
    notes: Optional[str] = None
) -> db_models.Reconciliation:
    """
    Mark a reconciliation as complete

    This should only be done when:
    1. The difference is zero (or within tolerance)
    2. Any discrepancies have been investigated and resolved
    """
    db_reconciliation = get_reconciliation_by_id(db, reconciliation_id, user_id)

    if not db_reconciliation:
        raise ValueError("Reconciliation not found")

    if db_reconciliation.status == db_models.ReconciliationStatus.RECONCILED:
        raise ValueError("Reconciliation already completed")

    # Check if there's a significant discrepancy
    if abs(db_reconciliation.difference) > Decimal("0.01"):
        raise ValueError(
            f"Cannot complete reconciliation with discrepancy of {db_reconciliation.difference}. "
            "Please investigate and resolve the difference first."
        )

    # Mark as reconciled
    db_reconciliation.status = db_models.ReconciliationStatus.RECONCILED
    db_reconciliation.reconciled_by = user_id
    db_reconciliation.reconciled_at = datetime.utcnow()

    if notes:
        db_reconciliation.notes = notes

    db.commit()
    db.refresh(db_reconciliation)

    return db_reconciliation


def get_reconciliation_status_by_account(
    db: Session,
    user_id: UUID
) -> List[dict]:
    """
    Get reconciliation status for all user's accounts

    Returns summary showing:
    - Last reconciliation date
    - Days since last reconciliation
    - Current reconciliation status
    """
    from sqlalchemy import func

    # Get all user's accounts
    accounts = db.query(db_models.Account).filter(
        db_models.Account.user_id == user_id,
        db_models.Account.is_active == True
    ).all()

    result = []
    today = date.today()

    for account in accounts:
        # Get last reconciliation
        last_recon = db.query(db_models.Reconciliation).filter(
            db_models.Reconciliation.account_id == account.id
        ).order_by(
            db_models.Reconciliation.reconciliation_date.desc()
        ).first()

        if last_recon:
            days_since = (today - last_recon.reconciliation_date).days
            needs_reconciliation = days_since > 7  # Flag if > 1 week
        else:
            days_since = None
            needs_reconciliation = True

        result.append({
            "account_id": account.id,
            "account_name": account.name,
            "account_type": account.account_type,
            "current_balance": account.current_balance,
            "last_reconciliation_date": last_recon.reconciliation_date if last_recon else None,
            "last_reconciliation_status": last_recon.status if last_recon else None,
            "days_since_reconciliation": days_since,
            "needs_reconciliation": needs_reconciliation
        })

    return result


def find_missing_transactions(
    db: Session,
    reconciliation_id: UUID,
    user_id: UUID
) -> dict:
    """
    Analyze a reconciliation with discrepancy to identify potential missing transactions

    Returns suggestions of what might be missing based on the difference amount
    """
    db_reconciliation = get_reconciliation_by_id(db, reconciliation_id, user_id)

    if not db_reconciliation:
        raise ValueError("Reconciliation not found")

    difference = db_reconciliation.difference

    if abs(difference) <= Decimal("0.01"):
        return {
            "has_discrepancy": False,
            "difference": difference,
            "suggestions": []
        }

    # Get recent transactions around reconciliation date
    from datetime import timedelta
    start_date = db_reconciliation.reconciliation_date - timedelta(days=30)
    end_date = db_reconciliation.reconciliation_date

    transactions = db.query(db_models.Transaction).filter(
        db_models.Transaction.account_id == db_reconciliation.account_id,
        db_models.Transaction.transaction_date >= start_date,
        db_models.Transaction.transaction_date <= end_date,
        db_models.Transaction.status != db_models.TransactionStatus.CANCELLED
    ).all()

    suggestions = []

    # If positive difference, we might be missing income or have extra expenses
    if difference > 0:
        suggestions.append({
            "type": "missing_income",
            "message": f"Your bank statement shows ${difference} more than the system. You might be missing income transactions.",
            "amount": difference
        })
    # If negative difference, we might be missing expenses or have extra income
    else:
        suggestions.append({
            "type": "missing_expense",
            "message": f"Your system shows ${abs(difference)} more than the bank statement. You might be missing expense transactions or have duplicate income entries.",
            "amount": abs(difference)
        })

    # Look for transactions matching the difference amount
    matching_transactions = [
        {
            "transaction_id": t.id,
            "date": t.transaction_date,
            "amount": t.amount,
            "description": t.description,
            "type": t.transaction_type
        }
        for t in transactions
        if abs(t.amount - abs(difference)) < Decimal("0.01")
    ]

    return {
        "has_discrepancy": True,
        "difference": difference,
        "reconciliation_date": db_reconciliation.reconciliation_date,
        "statement_balance": db_reconciliation.statement_balance,
        "system_balance": db_reconciliation.system_balance,
        "suggestions": suggestions,
        "matching_amount_transactions": matching_transactions
    }
