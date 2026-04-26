"""
Reconciliations API Endpoints
Bank Reconciliation Management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import date

from app.api.dependencies import get_db, get_current_active_user
from app.models import db_models, schemas
from app.services import reconciliation_service

router = APIRouter(prefix="/reconciliations", tags=["reconciliations"])


@router.post("", response_model=schemas.ReconciliationResponse, status_code=status.HTTP_201_CREATED)
def create_reconciliation(
    reconciliation: schemas.ReconciliationCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Create a new reconciliation record."""
    try:
        return reconciliation_service.create_reconciliation(
            db=db, reconciliation=reconciliation, user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[schemas.ReconciliationResponse])
def list_reconciliations(
    account_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status: Optional[db_models.ReconciliationStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """List reconciliations for the authenticated user."""
    return reconciliation_service.get_reconciliations(
        db=db,
        user_id=current_user.id,
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get("/status/summary")
def get_reconciliation_status_summary(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get reconciliation status summary for all user's accounts."""
    summary = reconciliation_service.get_reconciliation_status_by_account(
        db=db, user_id=current_user.id
    )
    return {
        "user_id": current_user.id,
        "accounts": summary,
        "total_accounts": len(summary),
        "accounts_needing_reconciliation": sum(1 for a in summary if a["needs_reconciliation"]),
    }


@router.get("/{reconciliation_id}", response_model=schemas.ReconciliationResponse)
def get_reconciliation(
    reconciliation_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get a reconciliation by ID."""
    db_reconciliation = reconciliation_service.get_reconciliation_by_id(
        db=db, reconciliation_id=reconciliation_id, user_id=current_user.id
    )
    if not db_reconciliation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reconciliation not found")
    return db_reconciliation


@router.put("/{reconciliation_id}", response_model=schemas.ReconciliationResponse)
def update_reconciliation(
    reconciliation_id: UUID,
    reconciliation_update: schemas.ReconciliationUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Update a reconciliation record."""
    try:
        return reconciliation_service.update_reconciliation(
            db=db,
            reconciliation_id=reconciliation_id,
            user_id=current_user.id,
            update_data=reconciliation_update,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{reconciliation_id}/complete", response_model=schemas.ReconciliationResponse)
def complete_reconciliation(
    reconciliation_id: UUID,
    complete_data: schemas.ReconciliationComplete,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Mark a reconciliation as complete."""
    try:
        return reconciliation_service.complete_reconciliation(
            db=db,
            reconciliation_id=reconciliation_id,
            user_id=current_user.id,
            notes=complete_data.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{reconciliation_id}/analyze")
def analyze_reconciliation_discrepancy(
    reconciliation_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Analyze a reconciliation with discrepancy."""
    try:
        return reconciliation_service.find_missing_transactions(
            db=db, reconciliation_id=reconciliation_id, user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
