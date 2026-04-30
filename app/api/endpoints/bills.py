"""
Bills API Endpoints
Recurring Bills Management (Utilities, Subscriptions, Rent, Insurance)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import date

from app.api.dependencies import get_db, get_current_active_user
from app.models import db_models, schemas
from app.services import bill_service

router = APIRouter(prefix="/bills", tags=["bills"])


@router.post("", response_model=schemas.BillResponse, status_code=status.HTTP_201_CREATED)
def create_bill(
    bill: schemas.BillCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Create a new recurring bill."""
    bill_data = bill.model_dump()
    bill_data["user_id"] = current_user.id
    bill_obj = schemas.BillCreate(**bill_data)
    try:
        return bill_service.create_bill(db=db, bill=bill_obj)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[schemas.BillResponse])
def list_bills(
    bill_type: Optional[db_models.BillType] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """List bills for the authenticated user."""
    return bill_service.get_bills(
        db=db,
        user_id=current_user.id,
        bill_type=bill_type,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@router.get("/upcoming", response_model=List[schemas.BillOccurrenceResponse])
def get_upcoming_bills(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get upcoming bills due in the next N days."""
    return bill_service.get_upcoming_bills(db=db, user_id=current_user.id, days=days)


@router.get("/overdue", response_model=List[schemas.BillOccurrenceResponse])
def get_overdue_bills(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get all overdue bills."""
    return bill_service.get_overdue_bills(db=db, user_id=current_user.id)


@router.get("/summary")
def get_bills_summary(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get bills summary."""
    return bill_service.get_bills_summary(db=db, user_id=current_user.id)


@router.post("/generate-occurrences")
def generate_bill_occurrences(
    months_ahead: int = Query(3, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Auto-generate bill occurrences for the next N months."""
    try:
        count = bill_service.generate_next_occurrences(
            db=db, user_id=current_user.id, months_ahead=months_ahead
        )
        return {"message": f"Generated {count} bill occurrences", "occurrences_created": count, "months_ahead": months_ahead}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error generating occurrences: {str(e)}")


@router.get("/{bill_id:uuid}", response_model=schemas.BillResponse)
def get_bill(
    bill_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get a bill by ID."""
    db_bill = bill_service.get_bill_by_id(db=db, bill_id=bill_id, user_id=current_user.id)
    if not db_bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return db_bill


@router.put("/{bill_id:uuid}", response_model=schemas.BillResponse)
def update_bill(
    bill_id: UUID,
    bill_update: schemas.BillUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Update a bill."""
    try:
        return bill_service.update_bill(db=db, bill_id=bill_id, user_id=current_user.id, update_data=bill_update)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{bill_id:uuid}", response_model=schemas.BillResponse)
def delete_bill(
    bill_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Deactivate a bill (soft delete)."""
    try:
        return bill_service.delete_bill(db=db, bill_id=bill_id, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# BILL OCCURRENCES
# ============================================================================

@router.post("/occurrences", response_model=schemas.BillOccurrenceResponse, status_code=status.HTTP_201_CREATED)
def create_bill_occurrence(
    occurrence: schemas.BillOccurrenceCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Create a bill occurrence manually."""
    try:
        return bill_service.create_bill_occurrence(db=db, occurrence=occurrence, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/occurrences", response_model=List[schemas.BillOccurrenceResponse])
def list_bill_occurrences(
    bill_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status: Optional[db_models.BillStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """List bill occurrences for the authenticated user."""
    return bill_service.get_bill_occurrences(
        db=db,
        user_id=current_user.id,
        bill_id=bill_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get("/occurrences/{occurrence_id}", response_model=schemas.BillOccurrenceResponse)
def get_bill_occurrence(
    occurrence_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get a bill occurrence by ID."""
    db_occurrence = bill_service.get_bill_occurrence_by_id(
        db=db, occurrence_id=occurrence_id, user_id=current_user.id
    )
    if not db_occurrence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill occurrence not found")
    return db_occurrence


@router.put("/occurrences/{occurrence_id}", response_model=schemas.BillOccurrenceResponse)
def update_bill_occurrence(
    occurrence_id: UUID,
    occurrence_update: schemas.BillOccurrenceUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Update a bill occurrence."""
    try:
        return bill_service.update_bill_occurrence(
            db=db, occurrence_id=occurrence_id, user_id=current_user.id, update_data=occurrence_update
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/occurrences/{occurrence_id}/pay", response_model=schemas.BillOccurrenceResponse)
def pay_bill_occurrence(
    occurrence_id: UUID,
    payment: schemas.BillOccurrencePayment,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Mark a bill occurrence as paid."""
    try:
        return bill_service.mark_bill_occurrence_as_paid(
            db=db, occurrence_id=occurrence_id, user_id=current_user.id, payment_data=payment
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
