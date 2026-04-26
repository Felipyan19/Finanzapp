"""
Journal Entries API Endpoints
Double-Entry Bookkeeping
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import date

from app.api.dependencies import get_db, get_current_active_user
from app.models import db_models, schemas
from app.services import journal_entry_service

router = APIRouter(prefix="/journal-entries", tags=["journal-entries"])


@router.post("", response_model=schemas.JournalEntryResponse, status_code=status.HTTP_201_CREATED)
def create_journal_entry(
    entry: schemas.JournalEntryCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Create a new journal entry (in DRAFT status)."""
    entry_data = entry.model_dump()
    entry_data["user_id"] = current_user.id
    entry_obj = schemas.JournalEntryCreate(**entry_data)
    try:
        return journal_entry_service.create_journal_entry(db, entry_obj)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[schemas.JournalEntryResponse])
def list_journal_entries(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status: Optional[db_models.EntryStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """List journal entries for the authenticated user."""
    return journal_entry_service.get_journal_entries(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get("/accounts/{account_id}/ledger")
def get_account_ledger(
    account_id: UUID,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get account ledger with running balance."""
    try:
        ledger = journal_entry_service.get_account_ledger(
            db=db,
            account_id=account_id,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
        )
        return {"account_id": account_id, "start_date": start_date, "end_date": end_date, "entries": ledger}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{entry_id}", response_model=schemas.JournalEntryResponse)
def get_journal_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get a journal entry by ID."""
    db_entry = journal_entry_service.get_journal_entry_by_id(db, entry_id, current_user.id)
    if not db_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    return db_entry


@router.post("/{entry_id}/post", response_model=schemas.JournalEntryResponse)
def post_journal_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Post a journal entry (make it final)."""
    try:
        return journal_entry_service.post_journal_entry(db, entry_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{entry_id}/void", response_model=schemas.JournalEntryResponse)
def void_journal_entry(
    entry_id: UUID,
    void_data: schemas.JournalEntryVoid,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Void a posted journal entry."""
    try:
        return journal_entry_service.void_journal_entry(
            db=db, entry_id=entry_id, user_id=current_user.id, reason=void_data.void_reason
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
