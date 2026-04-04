from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from app.models.db_models import (
    AccountType, CategoryType, TransactionType, TransactionStatus,
    TransactionSource, Frequency, PeriodType, GoalStatus,
    DebtType, DebtStatus, InvestmentType, MovementType
)


# ============================================================================
# USER SCHEMAS
# ============================================================================

class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    currency: str = Field(default="COP", max_length=3)
    timezone: str = Field(default="America/Bogota", max_length=50)


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    currency: Optional[str] = Field(None, max_length=3)
    timezone: Optional[str] = Field(None, max_length=50)


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# ACCOUNT SCHEMAS
# ============================================================================

class AccountBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    account_type: AccountType
    institution_name: Optional[str] = Field(None, max_length=255)
    currency: str = Field(default="COP", max_length=3)
    initial_balance: Decimal = Field(default=Decimal("0"), ge=0)


class AccountCreate(AccountBase):
    user_id: UUID


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    institution_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class AccountResponse(AccountBase):
    id: UUID
    user_id: UUID
    current_balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountBalanceResponse(BaseModel):
    account_id: UUID
    account_name: str
    current_balance: Decimal
    currency: str


# ============================================================================
# CATEGORY SCHEMAS
# ============================================================================

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category_type: CategoryType
    parent_id: Optional[UUID] = None
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$")


class CategoryCreate(CategoryBase):
    user_id: UUID


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$")
    is_active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    id: UUID
    user_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# TRANSACTION SCHEMAS
# ============================================================================

class TransactionBase(BaseModel):
    transaction_type: TransactionType
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="COP", max_length=3)
    account_id: UUID
    counterparty_account_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    transaction_date: date
    description: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None


class TransactionCreate(TransactionBase):
    user_id: UUID
    status: TransactionStatus = TransactionStatus.CONFIRMED
    source: TransactionSource = TransactionSource.MANUAL


class TransactionUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0)
    category_id: Optional[UUID] = None
    transaction_date: Optional[date] = None
    description: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    status: Optional[TransactionStatus] = None


class TransactionResponse(TransactionBase):
    id: UUID
    user_id: UUID
    status: TransactionStatus
    source: TransactionSource
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionSummary(BaseModel):
    total_income: Decimal
    total_expense: Decimal
    net_balance: Decimal
    transaction_count: int
    period_start: date
    period_end: date


class TransactionByCategory(BaseModel):
    category_id: Optional[UUID]
    category_name: Optional[str]
    total_amount: Decimal
    transaction_count: int
    percentage: Decimal


class MonthlyHistory(BaseModel):
    month: date
    total_income: Decimal
    total_expense: Decimal
    net_balance: Decimal
    transaction_count: int


# ============================================================================
# RECURRING TRANSACTION SCHEMAS
# ============================================================================

class RecurringTransactionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    transaction_type: TransactionType
    amount: Decimal = Field(..., gt=0)
    frequency: Frequency
    interval_value: int = Field(default=1, ge=1)
    account_id: UUID
    category_id: Optional[UUID] = None
    start_date: date
    end_date: Optional[date] = None
    auto_create: bool = False


class RecurringTransactionCreate(RecurringTransactionBase):
    user_id: UUID


class RecurringTransactionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    amount: Optional[Decimal] = Field(None, gt=0)
    frequency: Optional[Frequency] = None
    interval_value: Optional[int] = Field(None, ge=1)
    category_id: Optional[UUID] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None
    auto_create: Optional[bool] = None


class RecurringTransactionResponse(RecurringTransactionBase):
    id: UUID
    user_id: UUID
    next_execution_date: date
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# BUDGET SCHEMAS
# ============================================================================

class BudgetBase(BaseModel):
    category_id: UUID
    amount: Decimal = Field(..., gt=0)
    period_type: PeriodType
    start_date: date
    end_date: date
    rollover: bool = False


class BudgetCreate(BudgetBase):
    user_id: UUID


class BudgetUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0)
    period_type: Optional[PeriodType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    rollover: Optional[bool] = None
    is_active: Optional[bool] = None


class BudgetResponse(BudgetBase):
    id: UUID
    user_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetProgress(BaseModel):
    budget_id: UUID
    category_name: str
    budget_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    percentage_used: Decimal
    is_exceeded: bool
    period_start: date
    period_end: date


# ============================================================================
# FINANCIAL GOAL SCHEMAS
# ============================================================================

class FinancialGoalBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    target_amount: Decimal = Field(..., gt=0)
    target_date: Optional[date] = None
    account_id: Optional[UUID] = None
    priority: int = Field(default=1, ge=1)


class FinancialGoalCreate(FinancialGoalBase):
    user_id: UUID


class FinancialGoalUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    target_amount: Optional[Decimal] = Field(None, gt=0)
    target_date: Optional[date] = None
    account_id: Optional[UUID] = None
    status: Optional[GoalStatus] = None
    priority: Optional[int] = Field(None, ge=1)


class FinancialGoalResponse(FinancialGoalBase):
    id: UUID
    user_id: UUID
    current_amount: Decimal
    status: GoalStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalContribution(BaseModel):
    amount: Decimal = Field(..., gt=0)


class GoalProgress(BaseModel):
    goal_id: UUID
    goal_name: str
    target_amount: Decimal
    current_amount: Decimal
    remaining_amount: Decimal
    percentage_complete: Decimal
    is_completed: bool
    target_date: Optional[date]
    estimated_completion_date: Optional[date]


# ============================================================================
# ATTACHMENT SCHEMAS
# ============================================================================

class AttachmentResponse(BaseModel):
    id: UUID
    transaction_id: UUID
    file_url: str
    file_name: str
    mime_type: Optional[str]
    file_size: Optional[int]
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# TAG SCHEMAS
# ============================================================================

class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = Field(None, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagCreate(TagBase):
    user_id: UUID


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, max_length=7, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagResponse(TagBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# DEBT SCHEMAS
# ============================================================================

class DebtBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    debt_type: DebtType
    principal_amount: Decimal = Field(..., gt=0)
    interest_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    lender_or_borrower: Optional[str] = Field(None, max_length=255)
    currency: str = Field(default="COP", max_length=3)
    start_date: date
    due_date: Optional[date] = None
    notes: Optional[str] = None


class DebtCreate(DebtBase):
    user_id: UUID


class DebtUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    current_balance: Optional[Decimal] = Field(None, ge=0)
    interest_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    lender_or_borrower: Optional[str] = Field(None, max_length=255)
    due_date: Optional[date] = None
    status: Optional[DebtStatus] = None
    notes: Optional[str] = None


class DebtResponse(DebtBase):
    id: UUID
    user_id: UUID
    current_balance: Decimal
    status: DebtStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DebtPaymentBase(BaseModel):
    debt_id: UUID
    transaction_id: Optional[UUID] = None
    payment_amount: Decimal = Field(..., gt=0)
    principal_component: Decimal = Field(..., ge=0)
    interest_component: Decimal = Field(default=Decimal("0"), ge=0)
    payment_date: date
    notes: Optional[str] = None


class DebtPaymentCreate(DebtPaymentBase):
    pass


class DebtPaymentUpdate(BaseModel):
    payment_amount: Optional[Decimal] = Field(None, gt=0)
    principal_component: Optional[Decimal] = Field(None, ge=0)
    interest_component: Optional[Decimal] = Field(None, ge=0)
    payment_date: Optional[date] = None
    notes: Optional[str] = None


class DebtPaymentResponse(DebtPaymentBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# INVESTMENT SCHEMAS
# ============================================================================

class InvestmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    investment_type: InvestmentType
    platform_name: Optional[str] = Field(None, max_length=255)
    currency: str = Field(default="COP", max_length=3)
    initial_value: Decimal = Field(default=Decimal("0"), ge=0)
    notes: Optional[str] = None


class InvestmentCreate(InvestmentBase):
    user_id: UUID


class InvestmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    platform_name: Optional[str] = Field(None, max_length=255)
    current_value: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class InvestmentResponse(InvestmentBase):
    id: UUID
    user_id: UUID
    current_value: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvestmentMovementBase(BaseModel):
    investment_id: UUID
    transaction_id: Optional[UUID] = None
    movement_type: MovementType
    amount: Decimal = Field(..., gt=0)
    movement_date: date
    notes: Optional[str] = None


class InvestmentMovementCreate(InvestmentMovementBase):
    pass


class InvestmentMovementUpdate(BaseModel):
    movement_type: Optional[MovementType] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    movement_date: Optional[date] = None
    notes: Optional[str] = None


class InvestmentMovementResponse(InvestmentMovementBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# HEALTH CHECK SCHEMA
# ============================================================================

class HealthCheckResponse(BaseModel):
    status: str
    database: str
    version: str
    timestamp: datetime
