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


# Models
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
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
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", foreign_keys="Transaction.account_id", back_populates="account")
    counterparty_transactions = relationship("Transaction", foreign_keys="Transaction.counterparty_account_id", back_populates="counterparty_account")
    recurring_transactions = relationship("RecurringTransaction", back_populates="account")
    financial_goals = relationship("FinancialGoal", back_populates="account")

    __table_args__ = (
        CheckConstraint("initial_balance >= 0", name="check_initial_balance_positive"),
        Index("idx_account_user_active", "user_id", "is_active"),
    )

    def __repr__(self):
        return f"<Account(id={self.id}, name={self.name}, type={self.account_type}, balance={self.current_balance})>"


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
    metadata = Column(JSONB)
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
