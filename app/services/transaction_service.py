from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from decimal import Decimal
from datetime import date
from typing import List, Tuple, Optional
from uuid import UUID

from app.models import db_models, schemas


def update_account_balance(db: Session, account_id: UUID) -> Decimal:
    """
    Recalculate account balance based on all completed transactions.
    Returns the new balance.
    """
    account = db.query(db_models.Account).filter(db_models.Account.id == account_id).first()
    if not account:
        return Decimal("0")

    # Start with initial balance
    balance = account.initial_balance

    # Get all completed transactions for this account
    transactions = db.query(db_models.Transaction).filter(
        db_models.Transaction.account_id == account_id,
        db_models.Transaction.status == db_models.TransactionStatus.COMPLETED
    ).all()

    for transaction in transactions:
        if transaction.transaction_type == db_models.TransactionType.INCOME:
            balance += transaction.amount
        elif transaction.transaction_type == db_models.TransactionType.EXPENSE:
            balance -= transaction.amount
        elif transaction.transaction_type == db_models.TransactionType.ADJUSTMENT:
            balance += transaction.amount
        elif transaction.transaction_type == db_models.TransactionType.TRANSFER:
            # For transfers, amount is negative for source, positive for destination
            # This is handled during transaction creation
            if transaction.counterparty_account_id:
                balance -= transaction.amount

    # Update account balance
    account.current_balance = balance
    db.commit()

    return balance


def create_transaction(
    db: Session,
    transaction: schemas.TransactionCreate
) -> db_models.Transaction:
    """
    Create a new transaction and update account balance.
    """
    # Verify account exists
    account = db.query(db_models.Account).filter(db_models.Account.id == transaction.account_id).first()
    if not account:
        raise ValueError("Account not found")

    # Verify user owns the account
    if account.user_id != transaction.user_id:
        raise ValueError("Account does not belong to user")

    # Verify category if provided
    if transaction.category_id:
        category = db.query(db_models.Category).filter(db_models.Category.id == transaction.category_id).first()
        if not category:
            raise ValueError("Category not found")
        if category.user_id != transaction.user_id:
            raise ValueError("Category does not belong to user")

    # Create transaction
    db_transaction = db_models.Transaction(**transaction.model_dump())
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    # Update account balance if transaction is completed
    if transaction.status == db_models.TransactionStatus.COMPLETED:
        update_account_balance(db, transaction.account_id)

    return db_transaction


def create_transfer(
    db: Session,
    user_id: UUID,
    from_account_id: UUID,
    to_account_id: UUID,
    amount: Decimal,
    transaction_date: date,
    description: str = None
) -> Tuple[db_models.Transaction, db_models.Transaction]:
    """
    Create a transfer between two accounts (creates 2 transactions).
    Returns tuple of (source_transaction, destination_transaction).
    """
    # Verify both accounts exist and belong to user
    from_account = db.query(db_models.Account).filter(db_models.Account.id == from_account_id).first()
    to_account = db.query(db_models.Account).filter(db_models.Account.id == to_account_id).first()

    if not from_account or not to_account:
        raise ValueError("One or both accounts not found")

    if from_account.user_id != user_id or to_account.user_id != user_id:
        raise ValueError("Accounts do not belong to user")

    if from_account_id == to_account_id:
        raise ValueError("Cannot transfer to the same account")

    # Create outgoing transaction (expense from source account)
    source_transaction = db_models.Transaction(
        user_id=user_id,
        transaction_type=db_models.TransactionType.TRANSFER,
        amount=amount,
        account_id=from_account_id,
        counterparty_account_id=to_account_id,
        transaction_date=transaction_date,
        description=description or f"Transfer to {to_account.name}",
        status=db_models.TransactionStatus.COMPLETED,
        source=db_models.TransactionSource.MANUAL
    )

    # Create incoming transaction (income to destination account)
    dest_transaction = db_models.Transaction(
        user_id=user_id,
        transaction_type=db_models.TransactionType.TRANSFER,
        amount=amount,
        account_id=to_account_id,
        counterparty_account_id=from_account_id,
        transaction_date=transaction_date,
        description=description or f"Transfer from {from_account.name}",
        status=db_models.TransactionStatus.COMPLETED,
        source=db_models.TransactionSource.MANUAL
    )

    db.add(source_transaction)
    db.add(dest_transaction)
    db.commit()
    db.refresh(source_transaction)
    db.refresh(dest_transaction)

    # Update both account balances
    update_account_balance(db, from_account_id)
    update_account_balance(db, to_account_id)

    return source_transaction, dest_transaction


def get_summary(
    db: Session,
    user_id: UUID,
    start_date: date,
    end_date: date,
    account_id: UUID = None
) -> schemas.TransactionSummary:
    """
    Get transaction summary for a period.
    """
    query = db.query(db_models.Transaction).filter(
        db_models.Transaction.user_id == user_id,
        db_models.Transaction.transaction_date >= start_date,
        db_models.Transaction.transaction_date <= end_date,
        db_models.Transaction.status == db_models.TransactionStatus.COMPLETED
    )

    if account_id:
        query = query.filter(db_models.Transaction.account_id == account_id)

    transactions = query.all()

    total_income = Decimal("0")
    total_expense = Decimal("0")

    for transaction in transactions:
        if transaction.transaction_type == db_models.TransactionType.INCOME:
            total_income += transaction.amount
        elif transaction.transaction_type == db_models.TransactionType.EXPENSE:
            total_expense += transaction.amount
        # Transfers are not counted in income/expense totals

    net_balance = total_income - total_expense

    return schemas.TransactionSummary(
        total_income=total_income,
        total_expense=total_expense,
        net_balance=net_balance,
        transaction_count=len(transactions),
        period_start=start_date,
        period_end=end_date
    )


def get_by_category(
    db: Session,
    user_id: UUID,
    start_date: date,
    end_date: date,
    transaction_type: str = None
) -> List[schemas.TransactionByCategory]:
    """
    Get transactions grouped by category for a period.
    """
    query = db.query(
        db_models.Transaction.category_id,
        db_models.Category.name,
        func.sum(db_models.Transaction.amount).label('total_amount'),
        func.count(db_models.Transaction.id).label('transaction_count')
    ).outerjoin(
        db_models.Category,
        db_models.Transaction.category_id == db_models.Category.id
    ).filter(
        db_models.Transaction.user_id == user_id,
        db_models.Transaction.transaction_date >= start_date,
        db_models.Transaction.transaction_date <= end_date,
        db_models.Transaction.status == db_models.TransactionStatus.COMPLETED
    )

    if transaction_type:
        query = query.filter(db_models.Transaction.transaction_type == transaction_type)

    query = query.group_by(db_models.Transaction.category_id, db_models.Category.name)

    results = query.all()

    # Calculate total for percentage
    total = sum(r.total_amount for r in results)

    category_summaries = []
    for result in results:
        percentage = (result.total_amount / total * 100) if total > 0 else Decimal("0")
        category_summaries.append(
            schemas.TransactionByCategory(
                category_id=result.category_id,
                category_name=result.name or "Uncategorized",
                total_amount=result.total_amount,
                transaction_count=result.transaction_count,
                percentage=round(percentage, 2)
            )
        )

    return category_summaries
