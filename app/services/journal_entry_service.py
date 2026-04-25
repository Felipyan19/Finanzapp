"""
Journal Entry Service - Double-Entry Bookkeeping Logic
Handles creation, posting, and voiding of journal entries
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from app.models import db_models, schemas


def validate_journal_entry(entry_data: schemas.JournalEntryCreate) -> List[str]:
    """
    Validate journal entry before creation
    Returns list of validation errors (empty if valid)
    """
    errors = []

    # Must have at least 2 line items
    if len(entry_data.line_items) < 2:
        errors.append("Journal entry must have at least 2 line items")

    # Calculate totals
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    for line in entry_data.line_items:
        # Exactly one of debit or credit must be > 0
        if line.debit_amount > 0 and line.credit_amount > 0:
            errors.append(f"Line item cannot have both debit and credit amounts")
        elif line.debit_amount == 0 and line.credit_amount == 0:
            errors.append(f"Line item must have either debit or credit amount > 0")

        total_debit += line.debit_amount
        total_credit += line.credit_amount

    # Debits must equal credits
    if total_debit != total_credit:
        errors.append(
            f"Journal entry not balanced: debits={total_debit}, credits={total_credit}"
        )

    return errors


def create_journal_entry(
    db: Session,
    entry: schemas.JournalEntryCreate
) -> db_models.JournalEntry:
    """
    Create a new journal entry (in DRAFT status)
    """
    # Validate entry
    validation_errors = validate_journal_entry(entry)
    if validation_errors:
        raise ValueError(f"Validation errors: {', '.join(validation_errors)}")

    # Verify user exists
    user = db.query(db_models.User).filter(db_models.User.id == entry.user_id).first()
    if not user:
        raise ValueError("User not found")

    # Verify all accounts exist and belong to user
    for line in entry.line_items:
        account = db.query(db_models.Account).filter(
            db_models.Account.id == line.account_id
        ).first()
        if not account:
            raise ValueError(f"Account {line.account_id} not found")
        if account.user_id != entry.user_id:
            raise ValueError(f"Account {line.account_id} does not belong to user")

    # Create journal entry header
    db_entry = db_models.JournalEntry(
        user_id=entry.user_id,
        entry_number=entry.entry_number,
        entry_date=entry.entry_date,
        description=entry.description,
        reference=entry.reference,
        transaction_id=entry.transaction_id,
        status=db_models.EntryStatus.DRAFT
    )
    db.add(db_entry)
    db.flush()  # Get the ID

    # Create line items
    for line_data in entry.line_items:
        line = db_models.JournalEntryLine(
            journal_entry_id=db_entry.id,
            account_id=line_data.account_id,
            category_id=line_data.category_id,
            debit_amount=line_data.debit_amount,
            credit_amount=line_data.credit_amount,
            description=line_data.description
        )
        db.add(line)

    db.commit()
    db.refresh(db_entry)

    return db_entry


def post_journal_entry(
    db: Session,
    entry_id: UUID,
    user_id: UUID
) -> db_models.JournalEntry:
    """
    Post a journal entry (make it final)
    Updates account balances accordingly
    """
    # Get entry
    entry = db.query(db_models.JournalEntry).filter(
        db_models.JournalEntry.id == entry_id,
        db_models.JournalEntry.user_id == user_id
    ).first()

    if not entry:
        raise ValueError("Journal entry not found")

    if not entry.can_post():
        raise ValueError(
            f"Cannot post entry: status={entry.status}, "
            f"balanced={entry.is_balanced}, "
            f"lines={len(entry.line_items)}"
        )

    # Post the entry
    entry.post()

    # Update account balances
    for line in entry.line_items:
        account = db.query(db_models.Account).filter(
            db_models.Account.id == line.account_id
        ).first()

        if line.debit_amount > 0:
            # Debit increases asset/expense accounts, decreases liability/equity/income
            # For simplicity, we treat all debits as increasing balance
            account.current_balance += line.debit_amount
        else:
            # Credit decreases asset/expense accounts, increases liability/equity/income
            # For simplicity, we treat all credits as decreasing balance
            account.current_balance -= line.credit_amount

    db.commit()
    db.refresh(entry)

    return entry


def void_journal_entry(
    db: Session,
    entry_id: UUID,
    user_id: UUID,
    reason: str = None
) -> db_models.JournalEntry:
    """
    Void a posted journal entry
    Creates a reversing entry to maintain audit trail
    """
    # Get entry
    entry = db.query(db_models.JournalEntry).filter(
        db_models.JournalEntry.id == entry_id,
        db_models.JournalEntry.user_id == user_id
    ).first()

    if not entry:
        raise ValueError("Journal entry not found")

    if entry.status != db_models.EntryStatus.POSTED:
        raise ValueError("Can only void posted entries")

    # Void the original entry
    entry.void(reason)

    # Create reversing entry
    reversing_lines = []
    for line in entry.line_items:
        # Reverse debits and credits
        reversing_lines.append(
            schemas.JournalEntryLineCreate(
                account_id=line.account_id,
                category_id=line.category_id,
                debit_amount=line.credit_amount,  # Swap
                credit_amount=line.debit_amount,   # Swap
                description=f"VOID: {line.description or entry.description}"
            )
        )

    reversing_entry_data = schemas.JournalEntryCreate(
        user_id=user_id,
        entry_number=f"VOID-{entry.entry_number or entry.id}",
        entry_date=date.today(),
        description=f"VOID: {entry.description}",
        reference=f"VOID-{entry.reference or entry.id}",
        line_items=reversing_lines
    )

    # Create and post the reversing entry
    reversing_entry = create_journal_entry(db, reversing_entry_data)
    reversing_entry = post_journal_entry(db, reversing_entry.id, user_id)

    db.commit()
    db.refresh(entry)

    return entry


def get_journal_entries(
    db: Session,
    user_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[db_models.EntryStatus] = None,
    skip: int = 0,
    limit: int = 100
) -> List[db_models.JournalEntry]:
    """
    Get journal entries for a user with filters
    """
    query = db.query(db_models.JournalEntry).filter(
        db_models.JournalEntry.user_id == user_id
    )

    if start_date:
        query = query.filter(db_models.JournalEntry.entry_date >= start_date)

    if end_date:
        query = query.filter(db_models.JournalEntry.entry_date <= end_date)

    if status:
        query = query.filter(db_models.JournalEntry.status == status)

    query = query.order_by(db_models.JournalEntry.entry_date.desc())
    query = query.offset(skip).limit(limit)

    return query.all()


def get_journal_entry_by_id(
    db: Session,
    entry_id: UUID,
    user_id: UUID
) -> Optional[db_models.JournalEntry]:
    """
    Get a specific journal entry by ID
    """
    return db.query(db_models.JournalEntry).filter(
        db_models.JournalEntry.id == entry_id,
        db_models.JournalEntry.user_id == user_id
    ).first()


def get_account_ledger(
    db: Session,
    account_id: UUID,
    user_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[dict]:
    """
    Get ledger entries for an account (running balance)
    Returns list of entries with running balance
    """
    # Verify account belongs to user
    account = db.query(db_models.Account).filter(
        db_models.Account.id == account_id,
        db_models.Account.user_id == user_id
    ).first()

    if not account:
        raise ValueError("Account not found")

    # Get all posted journal entry lines for this account
    query = db.query(
        db_models.JournalEntryLine,
        db_models.JournalEntry
    ).join(
        db_models.JournalEntry,
        db_models.JournalEntryLine.journal_entry_id == db_models.JournalEntry.id
    ).filter(
        db_models.JournalEntryLine.account_id == account_id,
        db_models.JournalEntry.status == db_models.EntryStatus.POSTED
    )

    if start_date:
        query = query.filter(db_models.JournalEntry.entry_date >= start_date)

    if end_date:
        query = query.filter(db_models.JournalEntry.entry_date <= end_date)

    query = query.order_by(db_models.JournalEntry.entry_date, db_models.JournalEntry.created_at)

    results = query.all()

    # Calculate running balance
    ledger = []
    running_balance = account.initial_balance

    for line, entry in results:
        if line.debit_amount > 0:
            running_balance += line.debit_amount
            amount = line.debit_amount
            dr_cr = "DR"
        else:
            running_balance -= line.credit_amount
            amount = line.credit_amount
            dr_cr = "CR"

        ledger.append({
            "entry_id": entry.id,
            "entry_date": entry.entry_date,
            "entry_number": entry.entry_number,
            "description": line.description or entry.description,
            "reference": entry.reference,
            "debit": line.debit_amount,
            "credit": line.credit_amount,
            "amount": amount,
            "type": dr_cr,
            "balance": running_balance
        })

    return ledger
