"""
Journal Entries API Endpoints
Double-Entry Bookkeeping
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import date

from app.api.dependencies import get_db
from app.models import db_models, schemas
from app.services import journal_entry_service

router = APIRouter(prefix="/journal-entries", tags=["journal-entries"])


@router.post("", response_model=schemas.JournalEntryResponse, status_code=status.HTTP_201_CREATED)
def create_journal_entry(
    entry: schemas.JournalEntryCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new journal entry (in DRAFT status)

    A journal entry must:
    - Have at least 2 line items
    - Have balanced debits and credits (sum of debits = sum of credits)
    - Each line must have either debit OR credit amount (not both)
    """
    try:
        db_entry = journal_entry_service.create_journal_entry(db, entry)
        return db_entry
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[schemas.JournalEntryResponse])
def list_journal_entries(
    user_id: UUID = Query(..., description="User ID to filter entries"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    status: Optional[db_models.EntryStatus] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    List journal entries for a user with optional filters

    Filters:
    - start_date: Entries on or after this date
    - end_date: Entries on or before this date
    - status: DRAFT, POSTED, or VOID
    """
    entries = journal_entry_service.get_journal_entries(
        db=db,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        skip=skip,
        limit=limit
    )
    return entries


@router.post("/{entry_id}/post", response_model=schemas.JournalEntryResponse)
def post_journal_entry(
    entry_id: UUID,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Post a journal entry (make it final)

    Posting a journal entry:
    - Changes status from DRAFT to POSTED
    - Updates account balances
    - Makes the entry immutable (cannot be edited)
    - Sets posted_at timestamp

    Only DRAFT entries that are balanced can be posted.
    """
    try:
        db_entry = journal_entry_service.post_journal_entry(db, entry_id, user_id)
        return db_entry
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{entry_id}/void", response_model=schemas.JournalEntryResponse)
def void_journal_entry(
    entry_id: UUID,
    void_data: schemas.JournalEntryVoid,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Void a posted journal entry

    Voiding a journal entry:
    - Changes status from POSTED to VOID
    - Creates a reversing entry to undo the accounting impact
    - Maintains complete audit trail
    - Sets voided_at timestamp and void_reason

    Only POSTED entries can be voided.
    """
    try:
        db_entry = journal_entry_service.void_journal_entry(
            db=db,
            entry_id=entry_id,
            user_id=user_id,
            reason=void_data.void_reason
        )
        return db_entry
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/accounts/{account_id}/ledger")
def get_account_ledger(
    account_id: UUID,
    user_id: UUID = Query(..., description="User ID for authorization"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    db: Session = Depends(get_db)
):
    """
    Get account ledger (all journal entry lines with running balance)

    Returns all posted journal entry lines for an account, with:
    - Entry date, number, and description
    - Debit and credit amounts
    - Running balance after each transaction

    This is the classic accounting ledger view.
    """
    try:
        ledger = journal_entry_service.get_account_ledger(
            db=db,
            account_id=account_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        return {
            "account_id": account_id,
            "start_date": start_date,
            "end_date": end_date,
            "entries": ledger
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{entry_id}", response_model=schemas.JournalEntryResponse)
def get_journal_entry(
    entry_id: UUID,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: Session = Depends(get_db)
):
    """Get a journal entry by ID"""
    db_entry = journal_entry_service.get_journal_entry_by_id(db, entry_id, user_id)
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found"
        )
    return db_entry
