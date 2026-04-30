from calendar import monthrange
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import db_models


def _add_months_preserving_day(source: date, months: int) -> date:
    """Add months to a date while clamping the day to the target month length."""
    month_index = (source.month - 1) + months
    target_year = source.year + (month_index // 12)
    target_month = (month_index % 12) + 1
    target_day = min(source.day, monthrange(target_year, target_month)[1])
    return date(target_year, target_month, target_day)


def _first_day_of_month(value: date) -> date:
    return date(value.year, value.month, 1)


def roll_forward_monthly_fixed_transactions(
    db: Session,
    user_id: UUID,
    reference_date: Optional[date] = None,
) -> int:
    """
    Move past-month fixed tasks to the current month and reset them to pending.

    This keeps fixed tasks as monthly reminders instead of one-time items.
    """
    today = reference_date or date.today()
    month_start = _first_day_of_month(today)

    stale_items = (
        db.query(db_models.FixedTransaction)
        .filter(
            db_models.FixedTransaction.user_id == user_id,
            db_models.FixedTransaction.estimated_date < month_start,
        )
        .all()
    )

    if not stale_items:
        return 0

    updated = 0
    for item in stale_items:
        months_to_add = (today.year - item.estimated_date.year) * 12 + (today.month - item.estimated_date.month)
        if months_to_add <= 0:
            continue

        item.estimated_date = _add_months_preserving_day(item.estimated_date, months_to_add)
        item.status = db_models.FixedTransactionStatus.PENDING
        item.linked_transaction_id = None
        item.real_amount = None
        item.real_date = None
        item.real_source_account_id = None
        item.real_destination_account_id = None
        item.completion_notes = None
        updated += 1

    if updated:
        db.commit()

    return updated
