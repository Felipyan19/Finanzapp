"""
Reconciliations API Endpoints
Bank Reconciliation Management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import date

from app.api.dependencies import get_db
from app.models import db_models, schemas
from app.services import reconciliation_service

router = APIRouter(prefix="/reconciliations", tags=["reconciliations"])


@router.post("", response_model=schemas.ReconciliationResponse, status_code=status.HTTP_201_CREATED)
def create_reconciliation(
    reconciliation: schemas.ReconciliationCreate,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Create a new reconciliation record

    Process:
    1. Provide the statement balance from your bank
    2. System will automatically:
       - Get current system balance from the account
       - Calculate the difference
       - Set status based on whether it balances

    Status will be:
    - RECONCILED: if difference is ≤ 1 cent (essentially zero)
    - DISCREPANCY: if there's a meaningful difference
    """
    try:
        db_reconciliation = reconciliation_service.create_reconciliation(
            db=db,
            reconciliation=reconciliation,
            user_id=user_id
        )
        return db_reconciliation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[schemas.ReconciliationResponse])
def list_reconciliations(
    user_id: UUID = Query(..., description="User ID to filter reconciliations"),
    account_id: Optional[UUID] = Query(None, description="Filter by account"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    status: Optional[db_models.ReconciliationStatus] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    List reconciliations with optional filters

    Filters:
    - account_id: Show reconciliations for specific account
    - start_date: Reconciliations on or after this date
    - end_date: Reconciliations on or before this date
    - status: PENDING, IN_PROGRESS, RECONCILED, or DISCREPANCY
    """
    reconciliations = reconciliation_service.get_reconciliations(
        db=db,
        user_id=user_id,
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        skip=skip,
        limit=limit
    )
    return reconciliations


@router.put("/{reconciliation_id}", response_model=schemas.ReconciliationResponse)
def update_reconciliation(
    reconciliation_id: UUID,
    reconciliation_update: schemas.ReconciliationUpdate,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Update a reconciliation record

    You can update:
    - statement_balance: Will recalculate difference and status
    - status: Manually change status
    - notes: Add notes about the reconciliation

    Note: Cannot update reconciliations that are already completed (RECONCILED status)
    """
    try:
        db_reconciliation = reconciliation_service.update_reconciliation(
            db=db,
            reconciliation_id=reconciliation_id,
            user_id=user_id,
            update_data=reconciliation_update
        )
        return db_reconciliation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{reconciliation_id}/complete", response_model=schemas.ReconciliationResponse)
def complete_reconciliation(
    reconciliation_id: UUID,
    complete_data: schemas.ReconciliationComplete,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Mark a reconciliation as complete

    Requirements:
    - Difference must be ≤ 1 cent (essentially zero)
    - Any discrepancies must have been investigated and resolved

    This will:
    - Set status to RECONCILED
    - Record who completed it and when
    - Lock the record from further updates
    """
    try:
        db_reconciliation = reconciliation_service.complete_reconciliation(
            db=db,
            reconciliation_id=reconciliation_id,
            user_id=user_id,
            notes=complete_data.notes
        )
        return db_reconciliation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/status/summary")
def get_reconciliation_status_summary(
    user_id: UUID = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Get reconciliation status summary for all user's accounts

    Shows for each account:
    - Last reconciliation date
    - Days since last reconciliation
    - Whether reconciliation is needed (> 7 days)
    - Current account balance
    """
    summary = reconciliation_service.get_reconciliation_status_by_account(
        db=db,
        user_id=user_id
    )

    return {
        "user_id": user_id,
        "accounts": summary,
        "total_accounts": len(summary),
        "accounts_needing_reconciliation": sum(1 for a in summary if a["needs_reconciliation"])
    }


@router.get("/{reconciliation_id}/analyze")
def analyze_reconciliation_discrepancy(
    reconciliation_id: UUID,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Analyze a reconciliation with discrepancy

    This endpoint helps investigate why there's a difference between
    your bank statement and the system balance.

    Returns:
    - The difference amount and direction
    - Suggestions on what might be missing
    - Recent transactions that match the difference amount
    """
    try:
        analysis = reconciliation_service.find_missing_transactions(
            db=db,
            reconciliation_id=reconciliation_id,
            user_id=user_id
        )
        return analysis
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{reconciliation_id}", response_model=schemas.ReconciliationResponse)
def get_reconciliation(
    reconciliation_id: UUID,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: Session = Depends(get_db)
):
    """Get a reconciliation by ID"""
    db_reconciliation = reconciliation_service.get_reconciliation_by_id(
        db=db,
        reconciliation_id=reconciliation_id,
        user_id=user_id
    )

    if not db_reconciliation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reconciliation not found"
        )

    return db_reconciliation
