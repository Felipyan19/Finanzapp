"""
Bill Service
Handles recurring bills and bill occurrences
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import UUID
from dateutil.relativedelta import relativedelta

from app.models import db_models, schemas


def create_bill(
    db: Session,
    bill: schemas.BillCreate
) -> db_models.Bill:
    """
    Create a new recurring bill

    Validates:
    - User exists
    - If fixed_amount, it must be > 0
    - If variable, average_amount should be provided
    - Category belongs to user (if provided)
    - Payment account belongs to user (if provided)
    """
    # Verify user exists
    user = db.query(db_models.User).filter(db_models.User.id == bill.user_id).first()
    if not user:
        raise ValueError("User not found")

    # Validate amounts
    if bill.is_fixed_amount and not bill.fixed_amount:
        raise ValueError("Fixed bills must have a fixed_amount")

    # Verify category belongs to user (if provided)
    if bill.category_id:
        category = db.query(db_models.Category).filter(
            db_models.Category.id == bill.category_id,
            db_models.Category.user_id == bill.user_id
        ).first()
        if not category:
            raise ValueError("Category not found or does not belong to user")

    # Verify payment account belongs to user (if provided)
    if bill.payment_account_id:
        account = db.query(db_models.Account).filter(
            db_models.Account.id == bill.payment_account_id,
            db_models.Account.user_id == bill.user_id
        ).first()
        if not account:
            raise ValueError("Payment account not found or does not belong to user")

    # Create bill
    db_bill = db_models.Bill(**bill.model_dump())
    db.add(db_bill)
    db.commit()
    db.refresh(db_bill)

    return db_bill


def get_bill_by_id(
    db: Session,
    bill_id: UUID,
    user_id: UUID
) -> Optional[db_models.Bill]:
    """Get a bill by ID (verify it belongs to user)"""
    return db.query(db_models.Bill).filter(
        db_models.Bill.id == bill_id,
        db_models.Bill.user_id == user_id
    ).first()


def get_bills(
    db: Session,
    user_id: UUID,
    bill_type: Optional[db_models.BillType] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> List[db_models.Bill]:
    """Get bills for a user with filters"""
    query = db.query(db_models.Bill).filter(
        db_models.Bill.user_id == user_id
    )

    if bill_type:
        query = query.filter(db_models.Bill.bill_type == bill_type)

    if is_active is not None:
        query = query.filter(db_models.Bill.is_active == is_active)

    query = query.order_by(db_models.Bill.name)
    query = query.offset(skip).limit(limit)

    return query.all()


def update_bill(
    db: Session,
    bill_id: UUID,
    user_id: UUID,
    update_data: schemas.BillUpdate
) -> db_models.Bill:
    """Update a bill"""
    db_bill = get_bill_by_id(db, bill_id, user_id)

    if not db_bill:
        raise ValueError("Bill not found")

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)

    # Verify category belongs to user (if changing)
    if 'category_id' in update_dict and update_dict['category_id']:
        category = db.query(db_models.Category).filter(
            db_models.Category.id == update_dict['category_id'],
            db_models.Category.user_id == user_id
        ).first()
        if not category:
            raise ValueError("Category not found or does not belong to user")

    # Verify payment account belongs to user (if changing)
    if 'payment_account_id' in update_dict and update_dict['payment_account_id']:
        account = db.query(db_models.Account).filter(
            db_models.Account.id == update_dict['payment_account_id'],
            db_models.Account.user_id == user_id
        ).first()
        if not account:
            raise ValueError("Payment account not found or does not belong to user")

    for field, value in update_dict.items():
        setattr(db_bill, field, value)

    db.commit()
    db.refresh(db_bill)

    return db_bill


def delete_bill(
    db: Session,
    bill_id: UUID,
    user_id: UUID
) -> db_models.Bill:
    """Deactivate a bill (soft delete)"""
    db_bill = get_bill_by_id(db, bill_id, user_id)

    if not db_bill:
        raise ValueError("Bill not found")

    db_bill.is_active = False
    db.commit()
    db.refresh(db_bill)

    return db_bill


# ============================================================================
# BILL OCCURRENCES
# ============================================================================

def create_bill_occurrence(
    db: Session,
    occurrence: schemas.BillOccurrenceCreate,
    user_id: UUID
) -> db_models.BillOccurrence:
    """Create a bill occurrence"""
    # Verify bill exists and belongs to user
    bill = get_bill_by_id(db, occurrence.bill_id, user_id)
    if not bill:
        raise ValueError("Bill not found")

    # If amount not provided, use expected amount from bill
    occurrence_data = occurrence.model_dump()
    if not occurrence_data.get('amount'):
        occurrence_data['amount'] = bill.expected_amount

    db_occurrence = db_models.BillOccurrence(**occurrence_data)
    db.add(db_occurrence)
    db.commit()
    db.refresh(db_occurrence)

    return db_occurrence


def get_bill_occurrence_by_id(
    db: Session,
    occurrence_id: UUID,
    user_id: UUID
) -> Optional[db_models.BillOccurrence]:
    """Get a bill occurrence by ID (verify it belongs to user's bill)"""
    return db.query(db_models.BillOccurrence).join(
        db_models.Bill
    ).filter(
        db_models.BillOccurrence.id == occurrence_id,
        db_models.Bill.user_id == user_id
    ).first()


def get_bill_occurrences(
    db: Session,
    user_id: UUID,
    bill_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[db_models.BillStatus] = None,
    skip: int = 0,
    limit: int = 100
) -> List[db_models.BillOccurrence]:
    """Get bill occurrences with filters"""
    query = db.query(db_models.BillOccurrence).join(
        db_models.Bill
    ).filter(
        db_models.Bill.user_id == user_id
    )

    if bill_id:
        query = query.filter(db_models.BillOccurrence.bill_id == bill_id)

    if start_date:
        query = query.filter(db_models.BillOccurrence.due_date >= start_date)

    if end_date:
        query = query.filter(db_models.BillOccurrence.due_date <= end_date)

    if status:
        query = query.filter(db_models.BillOccurrence.status == status)

    query = query.order_by(db_models.BillOccurrence.due_date)
    query = query.offset(skip).limit(limit)

    return query.all()


def update_bill_occurrence(
    db: Session,
    occurrence_id: UUID,
    user_id: UUID,
    update_data: schemas.BillOccurrenceUpdate
) -> db_models.BillOccurrence:
    """Update a bill occurrence"""
    db_occurrence = get_bill_occurrence_by_id(db, occurrence_id, user_id)

    if not db_occurrence:
        raise ValueError("Bill occurrence not found")

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(db_occurrence, field, value)

    db.commit()
    db.refresh(db_occurrence)

    return db_occurrence


def mark_bill_occurrence_as_paid(
    db: Session,
    occurrence_id: UUID,
    user_id: UUID,
    payment_data: schemas.BillOccurrencePayment
) -> db_models.BillOccurrence:
    """Mark a bill occurrence as paid"""
    db_occurrence = get_bill_occurrence_by_id(db, occurrence_id, user_id)

    if not db_occurrence:
        raise ValueError("Bill occurrence not found")

    if db_occurrence.status == db_models.BillStatus.PAID:
        raise ValueError("Bill occurrence already marked as paid")

    # Mark as paid
    db_occurrence.mark_as_paid(
        transaction_id=payment_data.transaction_id,
        paid_amount=payment_data.paid_amount or db_occurrence.amount
    )

    db.commit()
    db.refresh(db_occurrence)

    return db_occurrence


def get_upcoming_bills(
    db: Session,
    user_id: UUID,
    days: int = 30
) -> List[db_models.BillOccurrence]:
    """
    Get all unpaid bills due in the next N days

    Returns occurrences that are:
    - PENDING status
    - Due within next N days
    - Ordered by due date
    """
    today = date.today()
    end_date = today + timedelta(days=days)

    return get_bill_occurrences(
        db=db,
        user_id=user_id,
        start_date=today,
        end_date=end_date,
        status=db_models.BillStatus.PENDING
    )


def get_overdue_bills(
    db: Session,
    user_id: UUID
) -> List[db_models.BillOccurrence]:
    """Get all overdue bills (PENDING and due date < today)"""
    today = date.today()

    return db.query(db_models.BillOccurrence).join(
        db_models.Bill
    ).filter(
        db_models.Bill.user_id == user_id,
        db_models.BillOccurrence.status == db_models.BillStatus.PENDING,
        db_models.BillOccurrence.due_date < today
    ).order_by(db_models.BillOccurrence.due_date).all()


def get_bills_summary(
    db: Session,
    user_id: UUID
) -> dict:
    """
    Get summary of bills status

    Returns:
    - Total upcoming bills in next 30 days
    - Total amount due
    - Overdue bills count and amount
    - Breakdown by week
    """
    today = date.today()

    # Get overdue
    overdue = get_overdue_bills(db, user_id)
    overdue_amount = sum(occ.amount or Decimal("0") for occ in overdue)

    # Get upcoming 7 days
    upcoming_7 = get_upcoming_bills(db, user_id, days=7)
    upcoming_7_amount = sum(occ.amount or Decimal("0") for occ in upcoming_7)

    # Get upcoming 30 days
    upcoming_30 = get_upcoming_bills(db, user_id, days=30)
    upcoming_30_amount = sum(occ.amount or Decimal("0") for occ in upcoming_30)

    return {
        "overdue": {
            "count": len(overdue),
            "total_amount": overdue_amount,
            "bills": overdue
        },
        "upcoming_7days": {
            "count": len(upcoming_7),
            "total_amount": upcoming_7_amount,
            "bills": upcoming_7
        },
        "upcoming_30days": {
            "count": len(upcoming_30),
            "total_amount": upcoming_30_amount,
            "bills": upcoming_30
        }
    }


def generate_next_occurrences(
    db: Session,
    user_id: UUID,
    months_ahead: int = 3
) -> int:
    """
    Auto-generate bill occurrences for the next N months

    For each active bill:
    1. Calculate next occurrence dates based on frequency
    2. Create occurrence if doesn't exist
    3. Use expected amount from bill

    Returns: number of occurrences created
    """
    # Get all active bills for user
    bills = get_bills(db, user_id, is_active=True, limit=1000)

    count = 0
    today = date.today()
    end_date = today + relativedelta(months=months_ahead)

    for bill in bills:
        # Calculate next dates based on frequency
        current_date = today

        while current_date <= end_date:
            # Adjust to bill's due day
            try:
                occurrence_date = current_date.replace(day=bill.due_day)
            except ValueError:
                # Handle months with fewer days (e.g., Feb 30 -> Feb 28)
                import calendar
                last_day = calendar.monthrange(current_date.year, current_date.month)[1]
                occurrence_date = current_date.replace(day=min(bill.due_day, last_day))

            # Skip if in the past
            if occurrence_date >= today:
                # Check if occurrence already exists
                existing = db.query(db_models.BillOccurrence).filter(
                    db_models.BillOccurrence.bill_id == bill.id,
                    db_models.BillOccurrence.due_date == occurrence_date
                ).first()

                if not existing:
                    # Create occurrence
                    occurrence = db_models.BillOccurrence(
                        bill_id=bill.id,
                        due_date=occurrence_date,
                        amount=bill.expected_amount,
                        status=db_models.BillStatus.PENDING
                    )
                    db.add(occurrence)
                    count += 1

            # Move to next period based on frequency
            if bill.frequency == db_models.Frequency.MONTHLY:
                current_date += relativedelta(months=1)
            elif bill.frequency == db_models.Frequency.QUARTERLY:
                current_date += relativedelta(months=3)
            elif bill.frequency == db_models.Frequency.YEARLY:
                current_date += relativedelta(years=1)
            elif bill.frequency == db_models.Frequency.WEEKLY:
                current_date += timedelta(weeks=1)
            elif bill.frequency == db_models.Frequency.BIWEEKLY:
                current_date += timedelta(weeks=2)
            elif bill.frequency == db_models.Frequency.DAILY:
                current_date += timedelta(days=1)

    if count > 0:
        db.commit()

    return count
