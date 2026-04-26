import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Numeric,
    Enum, ForeignKey, Text, Index, CheckConstraint, UniqueConstraint, TIMESTAMP
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


# Enums
class AccountType(str, enum.Enum):
    BANK = "bank"
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DIGITAL_WALLET = "digital_wallet"
    INVESTMENT = "investment"
    SAVINGS = "savings"


class CategoryType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"


class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    DEBT_PAYMENT = "debt_payment"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TransactionSource(str, enum.Enum):
    MANUAL = "manual"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    N8N = "n8n"
    IMPORT = "import"
    RECURRING = "recurring"
    API = "api"


class Frequency(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class PeriodType(str, enum.Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class GoalStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DebtType(str, enum.Enum):
    OWED_BY_ME = "owed_by_me"
    OWED_TO_ME = "owed_to_me"


class DebtStatus(str, enum.Enum):
    ACTIVE = "active"
    PAID = "paid"
    CANCELLED = "cancelled"


class InvestmentType(str, enum.Enum):
    CRYPTO = "crypto"
    STOCKS = "stocks"
    BONDS = "bonds"
    REAL_ESTATE = "real_estate"
    MUTUAL_FUNDS = "mutual_funds"
    OTHER = "other"


class MovementType(str, enum.Enum):
    CONTRIBUTION = "contribution"
    WITHDRAWAL = "withdrawal"
    DIVIDEND = "dividend"
    INTEREST = "interest"


class EntryStatus(str, enum.Enum):
    DRAFT = "draft"
    POSTED = "posted"
    VOID = "void"


class ReconciliationStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RECONCILED = "reconciled"
    DISCREPANCY = "discrepancy"


class BillType(str, enum.Enum):
    UTILITY = "utility"           # Water, electricity, gas
    SUBSCRIPTION = "subscription" # Netflix, Spotify, gym
    RENT = "rent"                 # Housing
    INSURANCE = "insurance"       # Health, car, life
    LOAN_PAYMENT = "loan_payment" # Mortgage, car loan
    OTHER = "other"


class BillStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    PARTIALLY_PAID = "partially_paid"
    CANCELLED = "cancelled"


class FixedTransactionStatus(str, enum.Enum):
    PENDING = "pendiente"
    COMPLETED = "completada"
    SKIPPED = "omitida"


class PriorityLevel(str, enum.Enum):
    HIGH = "alta"
    MEDIUM = "media"
    LOW = "baja"


# Models
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=True)
    currency = Column(String(3), default="COP", nullable=False)
    timezone = Column(String(50), default="America/Bogota", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    recurring_transactions = relationship("RecurringTransaction", back_populates="user", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete-orphan")
    financial_goals = relationship("FinancialGoal", back_populates="user", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="user", cascade="all, delete-orphan")
    debts = relationship("Debt", back_populates="user", cascade="all, delete-orphan")
    investments = relationship("Investment", back_populates="user", cascade="all, delete-orphan")
    journal_entries = relationship("JournalEntry", back_populates="user", cascade="all, delete-orphan")
    fixed_transactions = relationship("FixedTransaction", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    account_type = Column(Enum(AccountType), nullable=False)
    institution_name = Column(String(255))
    currency = Column(String(3), default="COP", nullable=False)
    initial_balance = Column(Numeric(15, 2), default=0, nullable=False)
    current_balance = Column(Numeric(15, 2), default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Credit Card specific fields
    credit_limit = Column(Numeric(15, 2))  # Total credit limit
    available_credit = Column(Numeric(15, 2))  # Calculated: credit_limit - current_balance
    billing_cycle_day = Column(Integer)  # Day of month when billing cycle closes (1-31)
    payment_due_day = Column(Integer)  # Day of month when payment is due (1-31)
    minimum_payment_percentage = Column(Numeric(5, 2))  # Minimum payment % (e.g., 5.00 for 5%)
    interest_rate = Column(Numeric(5, 2))  # Annual interest rate (APR/TEA)
    grace_period_days = Column(Integer, default=21)  # Days before interest charged

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", foreign_keys="Transaction.account_id", back_populates="account")
    counterparty_transactions = relationship("Transaction", foreign_keys="Transaction.counterparty_account_id", back_populates="counterparty_account")
    recurring_transactions = relationship("RecurringTransaction", back_populates="account")
    financial_goals = relationship("FinancialGoal", back_populates="account")
    journal_entry_lines = relationship("JournalEntryLine", back_populates="account")

    __table_args__ = (
        CheckConstraint("initial_balance >= 0", name="check_initial_balance_positive"),
        Index("idx_account_user_active", "user_id", "is_active"),
    )

    def __repr__(self):
        return f"<Account(id={self.id}, name={self.name}, type={self.account_type}, balance={self.current_balance})>"

    @property
    def utilization_rate(self) -> Decimal:
        """
        Calculate credit utilization rate (important for credit score)
        Returns percentage of credit limit being used
        Only applicable for credit card accounts
        """
        if self.account_type == AccountType.CREDIT_CARD and self.credit_limit:
            if self.credit_limit > 0:
                return (self.current_balance / self.credit_limit) * 100
        return Decimal("0")

    def calculate_minimum_payment(self) -> Decimal:
        """
        Calculate minimum payment for current balance
        Only applicable for credit card accounts
        """
        if self.account_type == AccountType.CREDIT_CARD and self.minimum_payment_percentage:
            return self.current_balance * (self.minimum_payment_percentage / 100)
        return Decimal("0")

    def update_available_credit(self):
        """
        Update available credit based on current balance
        Should be called whenever current_balance changes
        """
        if self.account_type == AccountType.CREDIT_CARD and self.credit_limit:
            self.available_credit = self.credit_limit - self.current_balance


class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category_type = Column(Enum(CategoryType), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    icon = Column(String(50))
    color = Column(String(7))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="categories")
    parent = relationship("Category", remote_side=[id], backref="subcategories")
    transactions = relationship("Transaction", back_populates="category")
    recurring_transactions = relationship("RecurringTransaction", back_populates="category")
    budgets = relationship("Budget", back_populates="category")

    __table_args__ = (
        Index("idx_category_user_type", "user_id", "category_type"),
        Index("idx_category_parent", "parent_id"),
    )

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name}, type={self.category_type})>"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), default="COP", nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    counterparty_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    transaction_date = Column(Date, nullable=False, index=True)
    description = Column(String(500))
    notes = Column(Text)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.CONFIRMED, nullable=False)
    source = Column(Enum(TransactionSource), default=TransactionSource.MANUAL, nullable=False)
    metadata_json = Column("metadata", JSONB)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="transactions")
    account = relationship("Account", foreign_keys=[account_id], back_populates="transactions")
    counterparty_account = relationship("Account", foreign_keys=[counterparty_account_id], back_populates="counterparty_transactions")
    category = relationship("Category", back_populates="transactions")
    attachments = relationship("TransactionAttachment", back_populates="transaction", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary="transaction_tags", back_populates="transactions")
    debt_payments = relationship("DebtPayment", back_populates="transaction")
    investment_movements = relationship("InvestmentMovement", back_populates="transaction")

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_amount_positive"),
        Index("idx_transaction_user_date", "user_id", "transaction_date"),
        Index("idx_transaction_account_date", "account_id", "transaction_date"),
        Index("idx_transaction_category", "category_id"),
        Index("idx_transaction_type", "transaction_type"),
        Index("idx_transaction_status", "status"),
        Index("idx_transaction_source", "source"),
    )

    def __repr__(self):
        return f"<Transaction(id={self.id}, type={self.transaction_type}, amount={self.amount}, date={self.transaction_date})>"


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    frequency = Column(Enum(Frequency), nullable=False)
    interval_value = Column(Integer, default=1, nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    next_execution_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    auto_create = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="recurring_transactions")
    account = relationship("Account", back_populates="recurring_transactions")
    category = relationship("Category", back_populates="recurring_transactions")

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_recurring_amount_positive"),
        CheckConstraint("interval_value > 0", name="check_interval_positive"),
        Index("idx_recurring_user_active", "user_id", "is_active"),
        Index("idx_recurring_next_execution", "next_execution_date"),
    )

    def __repr__(self):
        return f"<RecurringTransaction(id={self.id}, name={self.name}, frequency={self.frequency})>"


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    period_type = Column(Enum(PeriodType), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    rollover = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_budget_amount_positive"),
        CheckConstraint("end_date > start_date", name="check_budget_dates_valid"),
        Index("idx_budget_user_active", "user_id", "is_active"),
        Index("idx_budget_category", "category_id"),
        Index("idx_budget_dates", "start_date", "end_date"),
    )

    def __repr__(self):
        return f"<Budget(id={self.id}, amount={self.amount}, period={self.period_type})>"


class FinancialGoal(Base):
    __tablename__ = "financial_goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    target_amount = Column(Numeric(15, 2), nullable=False)
    current_amount = Column(Numeric(15, 2), default=0, nullable=False)
    target_date = Column(Date, nullable=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(GoalStatus), default=GoalStatus.ACTIVE, nullable=False)
    priority = Column(Integer, default=1, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="financial_goals")
    account = relationship("Account", back_populates="financial_goals")

    __table_args__ = (
        CheckConstraint("target_amount > 0", name="check_goal_target_positive"),
        CheckConstraint("current_amount >= 0", name="check_goal_current_non_negative"),
        CheckConstraint("priority >= 1", name="check_goal_priority_positive"),
        Index("idx_goal_user_status", "user_id", "status"),
        Index("idx_goal_target_date", "target_date"),
    )

    def __repr__(self):
        return f"<FinancialGoal(id={self.id}, name={self.name}, target={self.target_amount}, current={self.current_amount})>"


class TransactionAttachment(Base):
    __tablename__ = "transaction_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    file_url = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500))
    mime_type = Column(String(100))
    file_size = Column(Integer)
    uploaded_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="attachments")

    def __repr__(self):
        return f"<TransactionAttachment(id={self.id}, filename={self.file_name})>"


class Tag(Base):
    __tablename__ = "tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    color = Column(String(7))
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="tags")
    transactions = relationship("Transaction", secondary="transaction_tags", back_populates="tags")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_tag_name"),
        Index("idx_tag_user", "user_id"),
    )

    def __repr__(self):
        return f"<Tag(id={self.id}, name={self.name})>"


class TransactionTag(Base):
    __tablename__ = "transaction_tags"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    __table_args__ = (
        Index("idx_transaction_tag", "transaction_id", "tag_id"),
    )


class Debt(Base):
    __tablename__ = "debts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    debt_type = Column(Enum(DebtType), nullable=False)
    principal_amount = Column(Numeric(15, 2), nullable=False)
    current_balance = Column(Numeric(15, 2), nullable=False)
    interest_rate = Column(Numeric(5, 2), nullable=True)
    lender_or_borrower = Column(String(255))
    currency = Column(String(3), default="COP", nullable=False)
    start_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    status = Column(Enum(DebtStatus), default=DebtStatus.ACTIVE, nullable=False)
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="debts")
    payments = relationship("DebtPayment", back_populates="debt", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("principal_amount > 0", name="check_debt_principal_positive"),
        CheckConstraint("current_balance >= 0", name="check_debt_balance_non_negative"),
        Index("idx_debt_user_status", "user_id", "status"),
        Index("idx_debt_type", "debt_type"),
    )

    def __repr__(self):
        return f"<Debt(id={self.id}, name={self.name}, type={self.debt_type}, balance={self.current_balance})>"


class DebtPayment(Base):
    __tablename__ = "debt_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    debt_id = Column(UUID(as_uuid=True), ForeignKey("debts.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)
    payment_amount = Column(Numeric(15, 2), nullable=False)
    principal_component = Column(Numeric(15, 2), nullable=False)
    interest_component = Column(Numeric(15, 2), default=0, nullable=False)
    payment_date = Column(Date, nullable=False)
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    debt = relationship("Debt", back_populates="payments")
    transaction = relationship("Transaction", back_populates="debt_payments")

    __table_args__ = (
        CheckConstraint("payment_amount > 0", name="check_payment_amount_positive"),
        CheckConstraint("principal_component >= 0", name="check_principal_non_negative"),
        CheckConstraint("interest_component >= 0", name="check_interest_non_negative"),
        Index("idx_debt_payment_debt", "debt_id"),
        Index("idx_debt_payment_date", "payment_date"),
    )

    def __repr__(self):
        return f"<DebtPayment(id={self.id}, amount={self.payment_amount}, date={self.payment_date})>"


class Investment(Base):
    __tablename__ = "investments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    investment_type = Column(Enum(InvestmentType), nullable=False)
    platform_name = Column(String(255))
    currency = Column(String(3), default="COP", nullable=False)
    initial_value = Column(Numeric(15, 2), default=0, nullable=False)
    current_value = Column(Numeric(15, 2), default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="investments")
    movements = relationship("InvestmentMovement", back_populates="investment", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_investment_user_active", "user_id", "is_active"),
        Index("idx_investment_type", "investment_type"),
    )

    def __repr__(self):
        return f"<Investment(id={self.id}, name={self.name}, type={self.investment_type}, value={self.current_value})>"


class InvestmentMovement(Base):
    __tablename__ = "investment_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investment_id = Column(UUID(as_uuid=True), ForeignKey("investments.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)
    movement_type = Column(Enum(MovementType), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    movement_date = Column(Date, nullable=False)
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    investment = relationship("Investment", back_populates="movements")
    transaction = relationship("Transaction", back_populates="investment_movements")

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_movement_amount_positive"),
        Index("idx_investment_movement_investment", "investment_id"),
        Index("idx_investment_movement_date", "movement_date"),
    )

    def __repr__(self):
        return f"<InvestmentMovement(id={self.id}, type={self.movement_type}, amount={self.amount}, date={self.movement_date})>"


# ============================================================================
# DOUBLE-ENTRY BOOKKEEPING MODELS
# ============================================================================

class JournalEntry(Base):
    """
    Journal Entry (Double-Entry Bookkeeping Header)
    Represents a complete accounting transaction with balanced debits and credits
    """
    __tablename__ = "journal_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_number = Column(String(50), nullable=True)  # Optional reference number
    entry_date = Column(Date, nullable=False, index=True)
    description = Column(String(500), nullable=False)
    reference = Column(String(100))  # Invoice #, Receipt #, etc.
    status = Column(Enum(EntryStatus), default=EntryStatus.DRAFT, nullable=False)

    # Link to original transaction (if created from Transaction)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)

    # Audit fields
    posted_at = Column(TIMESTAMP, nullable=True)
    voided_at = Column(TIMESTAMP, nullable=True)
    void_reason = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="journal_entries")
    transaction = relationship("Transaction", foreign_keys=[transaction_id])
    line_items = relationship("JournalEntryLine", back_populates="journal_entry", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_journal_entry_user_date", "user_id", "entry_date"),
        Index("idx_journal_entry_status", "status"),
        Index("idx_journal_entry_transaction", "transaction_id"),
    )

    def __repr__(self):
        return f"<JournalEntry(id={self.id}, date={self.entry_date}, status={self.status})>"

    @property
    def total_debit(self) -> Decimal:
        """Calculate total debit amount from all line items"""
        return sum(line.debit_amount for line in self.line_items)

    @property
    def total_credit(self) -> Decimal:
        """Calculate total credit amount from all line items"""
        return sum(line.credit_amount for line in self.line_items)

    @property
    def is_balanced(self) -> bool:
        """Check if entry is balanced (debits = credits)"""
        return self.total_debit == self.total_credit

    def can_post(self) -> bool:
        """Check if entry can be posted"""
        return (
            self.status == EntryStatus.DRAFT and
            self.is_balanced and
            len(self.line_items) >= 2  # At least one debit and one credit
        )

    def post(self):
        """Post the entry (make it final)"""
        if not self.can_post():
            raise ValueError(
                f"Cannot post entry: status={self.status}, "
                f"balanced={self.is_balanced}, "
                f"lines={len(self.line_items)}"
            )
        self.status = EntryStatus.POSTED
        self.posted_at = datetime.utcnow()

    def void(self, reason: str = None):
        """Void the entry"""
        if self.status != EntryStatus.POSTED:
            raise ValueError("Can only void posted entries")
        self.status = EntryStatus.VOID
        self.voided_at = datetime.utcnow()
        self.void_reason = reason


class JournalEntryLine(Base):
    """
    Journal Entry Line (Double-Entry Bookkeeping Detail)
    Represents a single debit or credit line in a journal entry
    """
    __tablename__ = "journal_entry_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    # Double-entry amounts (one must be zero, the other > 0)
    debit_amount = Column(Numeric(15, 2), default=0, nullable=False)
    credit_amount = Column(Numeric(15, 2), default=0, nullable=False)

    # Optional description for this specific line
    description = Column(String(500))

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    journal_entry = relationship("JournalEntry", back_populates="line_items")
    account = relationship("Account", back_populates="journal_entry_lines")
    category = relationship("Category")

    __table_args__ = (
        # Exactly one of debit or credit must be > 0, the other must be 0
        CheckConstraint(
            "(debit_amount > 0 AND credit_amount = 0) OR (debit_amount = 0 AND credit_amount > 0)",
            name="check_debit_or_credit_not_both"
        ),
        Index("idx_journal_line_entry", "journal_entry_id"),
        Index("idx_journal_line_account", "account_id"),
    )

    def __repr__(self):
        amount = self.debit_amount if self.debit_amount > 0 else self.credit_amount
        dr_cr = "DR" if self.debit_amount > 0 else "CR"
        return f"<JournalEntryLine(id={self.id}, account={self.account_id}, {dr_cr}={amount})>"

    @property
    def amount(self) -> Decimal:
        """Get the non-zero amount (either debit or credit)"""
        return self.debit_amount if self.debit_amount > 0 else self.credit_amount

    @property
    def is_debit(self) -> bool:
        """Check if this is a debit entry"""
        return self.debit_amount > 0

    @property
    def is_credit(self) -> bool:
        """Check if this is a credit entry"""
        return self.credit_amount > 0


# ============================================================================
# RECONCILIATION
# ============================================================================

class Reconciliation(Base):
    """
    Bank Reconciliation Records
    Weekly/Monthly reconciliation to verify account balances match bank statements
    """
    __tablename__ = "reconciliations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    reconciliation_date = Column(Date, nullable=False)

    # Balances
    statement_balance = Column(Numeric(15, 2), nullable=False)  # From bank statement
    system_balance = Column(Numeric(15, 2), nullable=False)     # From our system
    difference = Column(Numeric(15, 2), nullable=False)         # statement_balance - system_balance

    # Status and resolution
    status = Column(Enum(ReconciliationStatus), default=ReconciliationStatus.PENDING, nullable=False)
    notes = Column(Text)
    reconciled_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    reconciled_at = Column(TIMESTAMP)

    # Audit fields
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    account = relationship("Account")
    reconciled_by_user = relationship("User", foreign_keys=[reconciled_by])

    __table_args__ = (
        Index('idx_reconciliation_account_date', 'account_id', 'reconciliation_date'),
        Index('idx_reconciliation_status', 'status'),
    )

    def __repr__(self):
        return f"<Reconciliation(id={self.id}, account={self.account_id}, date={self.reconciliation_date}, status={self.status})>"

    @property
    def is_reconciled(self) -> bool:
        """Check if reconciliation is completed without discrepancy"""
        return self.status == ReconciliationStatus.RECONCILED and self.difference == Decimal("0")

    @property
    def has_discrepancy(self) -> bool:
        """Check if there's a difference between statement and system balance"""
        return abs(self.difference) > Decimal("0.01")  # Allow 1 cent tolerance

    def calculate_difference(self):
        """Calculate the difference between statement and system balance"""
        self.difference = self.statement_balance - self.system_balance

        # Auto-set status based on difference
        if abs(self.difference) <= Decimal("0.01"):
            self.status = ReconciliationStatus.RECONCILED
        elif self.status == ReconciliationStatus.PENDING:
            self.status = ReconciliationStatus.DISCREPANCY


# ============================================================================
# BILLS & INVOICES
# ============================================================================

class Bill(Base):
    """
    Recurring Bills (Utilities, Subscriptions, Rent, Insurance)
    Template for recurring bills with fixed or variable amounts
    """
    __tablename__ = "bills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # "Netflix", "Electricity", "Rent"
    bill_type = Column(Enum(BillType), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"))
    frequency = Column(Enum(Frequency), nullable=False)

    # Amount info
    is_fixed_amount = Column(Boolean, default=True, nullable=False)
    fixed_amount = Column(Numeric(15, 2))  # For fixed bills like Netflix
    average_amount = Column(Numeric(15, 2))  # For variable bills like electricity

    # Due date info
    due_day = Column(Integer, nullable=False)  # Day of month (1-31)
    reminder_days_before = Column(Integer, default=3, nullable=False)

    # Payment tracking
    auto_pay_enabled = Column(Boolean, default=False, nullable=False)
    payment_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"))

    # Metadata
    reference_number = Column(String(100))  # Account number, contract #
    notes = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit fields
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    category = relationship("Category")
    payment_account = relationship("Account", foreign_keys=[payment_account_id])
    occurrences = relationship("BillOccurrence", back_populates="bill", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_bills_user_id', 'user_id'),
        Index('idx_bills_user_active', 'user_id', 'is_active'),
    )

    def __repr__(self):
        return f"<Bill(id={self.id}, name={self.name}, type={self.bill_type}, amount={self.fixed_amount or self.average_amount})>"

    @property
    def expected_amount(self) -> Decimal:
        """Get expected amount for next occurrence"""
        return self.fixed_amount if self.is_fixed_amount else (self.average_amount or Decimal("0"))


class BillOccurrence(Base):
    """
    Individual Bill Instances
    Each occurrence represents a specific bill due on a specific date
    """
    __tablename__ = "bill_occurrences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bill_id = Column(UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True)
    due_date = Column(Date, nullable=False)
    amount = Column(Numeric(15, 2))  # Actual amount (may differ from expected for variable bills)
    status = Column(Enum(BillStatus), default=BillStatus.PENDING, nullable=False)

    # Payment tracking
    paid_date = Column(Date)
    paid_amount = Column(Numeric(15, 2))
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"))

    # Metadata
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    bill = relationship("Bill", back_populates="occurrences")
    transaction = relationship("Transaction")

    __table_args__ = (
        Index('idx_bill_occurrence_bill_id', 'bill_id'),
        Index('idx_bill_occurrence_due_date', 'due_date'),
        Index('idx_bill_occurrence_status', 'status'),
        Index('idx_bill_occurrence_bill_due', 'bill_id', 'due_date'),
    )

    def __repr__(self):
        return f"<BillOccurrence(id={self.id}, bill={self.bill_id}, due={self.due_date}, status={self.status})>"

    @property
    def is_overdue(self) -> bool:
        """Check if bill is overdue"""
        from datetime import date as dt_date
        return (
            self.status == BillStatus.PENDING and
            self.due_date < dt_date.today()
        )

    @property
    def days_until_due(self) -> int:
        """Calculate days until due date (negative if overdue)"""
        from datetime import date as dt_date
        delta = self.due_date - dt_date.today()
        return delta.days

    def mark_as_paid(self, transaction_id: UUID = None, paid_amount: Decimal = None):
        """Mark occurrence as paid"""
        from datetime import date as dt_date
        self.status = BillStatus.PAID
        self.paid_date = dt_date.today()
        self.paid_amount = paid_amount or self.amount
        self.transaction_id = transaction_id


class FixedTransaction(Base):
    """
    Monthly programmed financial tasks.
    They do not impact balances until completed.
    """
    __tablename__ = "fixed_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    estimated_amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), default="COP", nullable=False)
    estimated_date = Column(Date, nullable=False, index=True)
    status = Column(Enum(FixedTransactionStatus), default=FixedTransactionStatus.PENDING, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    priority = Column(Enum(PriorityLevel), default=PriorityLevel.MEDIUM, nullable=False)
    suggested_source_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    suggested_destination_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    description = Column(String(500))
    linked_transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)

    real_amount = Column(Numeric(15, 2), nullable=True)
    real_date = Column(Date, nullable=True)
    real_source_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    real_destination_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    completion_notes = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="fixed_transactions")
    category = relationship("Category")
    suggested_source_account = relationship("Account", foreign_keys=[suggested_source_account_id])
    suggested_destination_account = relationship("Account", foreign_keys=[suggested_destination_account_id])
    real_source_account = relationship("Account", foreign_keys=[real_source_account_id])
    real_destination_account = relationship("Account", foreign_keys=[real_destination_account_id])
    linked_transaction = relationship("Transaction", foreign_keys=[linked_transaction_id])

    __table_args__ = (
        CheckConstraint("estimated_amount > 0", name="check_fixed_estimated_amount_positive"),
        CheckConstraint("real_amount IS NULL OR real_amount > 0", name="check_fixed_real_amount_positive"),
        Index("idx_fixed_user_status", "user_id", "status"),
        Index("idx_fixed_user_estimated_date", "user_id", "estimated_date"),
    )
