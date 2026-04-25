"""
Bills API Endpoints
Recurring Bills Management (Utilities, Subscriptions, Rent, Insurance)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import date

from app.api.dependencies import get_db
from app.models import db_models, schemas
from app.services import bill_service

router = APIRouter(prefix="/bills", tags=["bills"])


@router.post("", response_model=schemas.BillResponse, status_code=status.HTTP_201_CREATED)
def create_bill(
    bill: schemas.BillCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new recurring bill

    Bill types:
    - UTILITY: Water, electricity, gas
    - SUBSCRIPTION: Netflix, Spotify, gym
    - RENT: Housing
    - INSURANCE: Health, car, life
    - LOAN_PAYMENT: Mortgage, car loan
    - OTHER: Other recurring bills

    Amount types:
    - Fixed: For bills with consistent amount (subscriptions)
    - Variable: For bills with varying amounts (utilities)
    """
    try:
        db_bill = bill_service.create_bill(db=db, bill=bill)
        return db_bill
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[schemas.BillResponse])
def list_bills(
    user_id: UUID = Query(..., description="User ID to filter bills"),
    bill_type: Optional[db_models.BillType] = Query(None, description="Filter by bill type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    List bills with optional filters

    Filters:
    - bill_type: UTILITY, SUBSCRIPTION, RENT, INSURANCE, LOAN_PAYMENT, OTHER
    - is_active: True for active bills, False for inactive
    """
    bills = bill_service.get_bills(
        db=db,
        user_id=user_id,
        bill_type=bill_type,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    return bills


@router.put("/{bill_id}", response_model=schemas.BillResponse)
def update_bill(
    bill_id: UUID,
    bill_update: schemas.BillUpdate,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: Session = Depends(get_db)
):
    """Update a bill"""
    try:
        db_bill = bill_service.update_bill(
            db=db,
            bill_id=bill_id,
            user_id=user_id,
            update_data=bill_update
        )
        return db_bill
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{bill_id}", response_model=schemas.BillResponse)
def delete_bill(
    bill_id: UUID,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Deactivate a bill (soft delete)

    This will mark the bill as inactive but preserve the record
    and all associated occurrences for historical tracking.
    """
    try:
        db_bill = bill_service.delete_bill(
            db=db,
            bill_id=bill_id,
            user_id=user_id
        )
        return db_bill
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# BILL OCCURRENCES
# ============================================================================

@router.post("/occurrences", response_model=schemas.BillOccurrenceResponse, status_code=status.HTTP_201_CREATED)
def create_bill_occurrence(
    occurrence: schemas.BillOccurrenceCreate,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Create a bill occurrence (individual instance)

    Normally occurrences are auto-generated, but you can create
    one manually if needed (e.g., for a one-time extra charge).
    """
    try:
        db_occurrence = bill_service.create_bill_occurrence(
            db=db,
            occurrence=occurrence,
            user_id=user_id
        )
        return db_occurrence
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/occurrences/{occurrence_id}", response_model=schemas.BillOccurrenceResponse)
def get_bill_occurrence(
    occurrence_id: UUID,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: Session = Depends(get_db)
):
    """Get a bill occurrence by ID"""
    db_occurrence = bill_service.get_bill_occurrence_by_id(
        db=db,
        occurrence_id=occurrence_id,
        user_id=user_id
    )

    if not db_occurrence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill occurrence not found"
        )

    return db_occurrence


@router.get("/occurrences", response_model=List[schemas.BillOccurrenceResponse])
def list_bill_occurrences(
    user_id: UUID = Query(..., description="User ID to filter occurrences"),
    bill_id: Optional[UUID] = Query(None, description="Filter by bill"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    status: Optional[db_models.BillStatus] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    List bill occurrences with filters

    Filters:
    - bill_id: Show occurrences for specific bill
    - start_date: Occurrences due on or after this date
    - end_date: Occurrences due on or before this date
    - status: PENDING, PAID, OVERDUE, PARTIALLY_PAID, CANCELLED
    """
    occurrences = bill_service.get_bill_occurrences(
        db=db,
        user_id=user_id,
        bill_id=bill_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        skip=skip,
        limit=limit
    )
    return occurrences


@router.put("/occurrences/{occurrence_id}", response_model=schemas.BillOccurrenceResponse)
def update_bill_occurrence(
    occurrence_id: UUID,
    occurrence_update: schemas.BillOccurrenceUpdate,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Update a bill occurrence

    You can update:
    - amount: Actual amount (for variable bills)
    - status: PENDING, PAID, OVERDUE, PARTIALLY_PAID, CANCELLED
    - notes: Add notes about this occurrence
    """
    try:
        db_occurrence = bill_service.update_bill_occurrence(
            db=db,
            occurrence_id=occurrence_id,
            user_id=user_id,
            update_data=occurrence_update
        )
        return db_occurrence
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/occurrences/{occurrence_id}/pay", response_model=schemas.BillOccurrenceResponse)
def pay_bill_occurrence(
    occurrence_id: UUID,
    payment: schemas.BillOccurrencePayment,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: Session = Depends(get_db)
):
    """
    Mark a bill occurrence as paid

    Optionally provide:
    - transaction_id: Link to the payment transaction
    - paid_amount: Amount actually paid (defaults to due amount)
    - paid_date: Payment date (defaults to today)
    """
    try:
        db_occurrence = bill_service.mark_bill_occurrence_as_paid(
            db=db,
            occurrence_id=occurrence_id,
            user_id=user_id,
            payment_data=payment
        )
        return db_occurrence
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/upcoming", response_model=List[schemas.BillOccurrenceResponse])
def get_upcoming_bills(
    user_id: UUID = Query(..., description="User ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days ahead to look"),
    db: Session = Depends(get_db)
):
    """
    Get upcoming bills due in the next N days

    Returns all PENDING bill occurrences with due dates
    within the next N days, ordered by due date.

    Default: Next 30 days
    """
    upcoming = bill_service.get_upcoming_bills(
        db=db,
        user_id=user_id,
        days=days
    )
    return upcoming


@router.get("/overdue", response_model=List[schemas.BillOccurrenceResponse])
def get_overdue_bills(
    user_id: UUID = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Get all overdue bills

    Returns all PENDING bill occurrences with due dates
    before today, ordered by due date (oldest first).
    """
    overdue = bill_service.get_overdue_bills(
        db=db,
        user_id=user_id
    )
    return overdue


@router.get("/summary")
def get_bills_summary(
    user_id: UUID = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Get bills summary

    Returns:
    - Overdue bills (count and total amount)
    - Upcoming in next 7 days
    - Upcoming in next 30 days
    """
    summary = bill_service.get_bills_summary(
        db=db,
        user_id=user_id
    )
    return summary


@router.post("/generate-occurrences")
def generate_bill_occurrences(
    user_id: UUID = Query(..., description="User ID"),
    months_ahead: int = Query(3, ge=1, le=12, description="Months ahead to generate"),
    db: Session = Depends(get_db)
):
    """
    Auto-generate bill occurrences for the next N months

    This will:
    1. Look at all active recurring bills
    2. Generate occurrences based on frequency
    3. Skip occurrences that already exist
    4. Use expected amount from bill

    Useful to run monthly or when new bills are created.

    Returns: Number of occurrences created
    """
    try:
        count = bill_service.generate_next_occurrences(
            db=db,
            user_id=user_id,
            months_ahead=months_ahead
        )
        return {
            "message": f"Generated {count} bill occurrences",
            "occurrences_created": count,
            "months_ahead": months_ahead
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating occurrences: {str(e)}"
        )


@router.get("/{bill_id}", response_model=schemas.BillResponse)
def get_bill(
    bill_id: UUID,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: Session = Depends(get_db)
):
    """Get a bill by ID"""
    db_bill = bill_service.get_bill_by_id(db=db, bill_id=bill_id, user_id=user_id)

    if not db_bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found"
        )

    return db_bill
