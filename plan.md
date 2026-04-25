# Plan Maestro MVP: Gestor de Finanzas Personales
## Revisión 2.0 - Abril 2026

**NOTA:** Ver `ANALISIS_TECNICO.md` para análisis completo de estructura, gaps y comparación con Firefly III, YNAB, Actual Budget.

---

## 1. Resumen Ejecutivo

### 1.1 Objetivo Principal
Construir un gestor de finanzas personales robusto que permita a usuarios poco organizados financieramente tener control total sobre:
- ✅ Múltiples fuentes de ingreso
- ✅ Gastos y gastos recurrentes
- ✅ Facturas y servicios (utilities, subscripciones)
- ✅ Tarjetas de crédito (con billing cycles, due dates)
- ✅ Créditos y deudas (con amortización)
- ✅ Presupuestos por categoría
- ✅ Reconciliación con bancos
- ✅ Reportes y diagnóstico mensual

### 1.2 Decisiones de Producto
- **Objetivo primario:** Diagnóstico mensual automático ("¿dónde se fue mi dinero?")
- **Métrica de éxito:** Tasa de ahorro neto + claridad (top 3 causas del gasto)
- **Carga de datos:** Manual (MVP), integraciones automáticas (Fase 2)
- **Cobertura:** Todas las cuentas, tarjetas, wallets del usuario
- **Multi-moneda:** Moneda base + tasas FX históricas
- **Calidad:** Clasificación completa por transacción + reconciliación semanal
- **Alertas:** Umbrales configurables (80% y 100% de presupuesto)

### 1.3 Estado Actual (Post-Análisis Técnico)

#### FORTALEZAS ✅
- Base sólida de datos: 10+ entidades bien estructuradas
- SQLAlchemy 2.0 + Pydantic v2 + FastAPI
- Índices estratégicos y constraints a nivel de BD
- Servicios de negocio separados (transaction, budget, goal)
- Docker + PostgreSQL ready

#### GAPS CRÍTICOS 🚨
1. **Double-Entry Bookkeeping:** Sistema simplificado (single-entry), no garantiza balance
2. **Tarjetas de Crédito:** Falta billing cycles, due dates, credit limits, interest tracking
3. **Facturas/Bills:** No hay entidad dedicada para utilities, subscripciones, etc.
4. **Reconciliación:** Tabla definida en plan pero NO implementada
5. **Multi-Currency:** No persiste FX rates ni base_amount en transacciones
6. **Split Transactions:** No se pueden dividir gastos en múltiples categorías
7. **Merchants:** No hay normalización de comercios
8. **Payment Methods:** No se trackea medio de pago (efectivo, débito, crédito)
9. **Transaction Immutability:** Se pueden editar/borrar (mala práctica contable)
10. **Balance Calculation:** Recalcula todo el historial (O(n)), no es eficiente

#### COMPARACIÓN CON REFERENTES
| Feature | FinanzApp | Firefly III | YNAB | Actual |
|---------|-----------|-------------|------|---------|
| Double-Entry | ❌ | ✅ | ⚠️ | ⚠️ |
| Credit Cards | ⚠️ | ✅ | ✅ | ✅ |
| Reconciliation | ❌ | ✅ | ✅ | ✅ |
| Split Transactions | ❌ | ✅ | ✅ | ✅ |
| Bills/Invoices | ⚠️ | ✅ | ✅ | ✅ |
| Multi-Currency | ⚠️ | ✅ | ✅ | ✅ |

Ver tabla completa en `ANALISIS_TECNICO.md` sección 7.

---

## 2. Implementación por Fases (Roadmap 8 Semanas)

### FASE 0: Fundamentos Contables (Semanas 1-2) 🔴 CRÍTICO

#### 2.0.1 Double-Entry Bookkeeping
**PROBLEMA:** Sistema actual usa single-entry (una transacción = un registro). No garantiza balance matemático.

**SOLUCIÓN:** Implementar doble partida contable:
```python
class JournalEntry(Base):
    """Journal entry (transaction) - header"""
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    entry_date: Mapped[date]
    description: Mapped[str]
    reference: Mapped[Optional[str]]  # Invoice #, Receipt #
    status: Mapped[EntryStatus]  # DRAFT, POSTED, VOID
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    line_items: Mapped[List["JournalEntryLine"]] = relationship()

    @validates('status')
    def validate_balanced(self, key, value):
        if value == EntryStatus.POSTED:
            total_debit = sum(line.debit_amount for line in self.line_items)
            total_credit = sum(line.credit_amount for line in self.line_items)
            if total_debit != total_credit:
                raise ValueError(f"Entry not balanced: DR={total_debit}, CR={total_credit}")
        return value

class JournalEntryLine(Base):
    """Journal entry line (debit or credit)"""
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    journal_entry_id: Mapped[UUID] = mapped_column(ForeignKey("journal_entries.id"))
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"))
    category_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("categories.id"))
    debit_amount: Mapped[Decimal] = mapped_column(default=Decimal("0"))
    credit_amount: Mapped[Decimal] = mapped_column(default=Decimal("0"))
    description: Mapped[Optional[str]]

    __table_args__ = (
        CheckConstraint(
            "(debit_amount > 0 AND credit_amount = 0) OR (debit_amount = 0 AND credit_amount > 0)",
            name="check_debit_or_credit_not_both"
        ),
    )
```

**BENEFICIOS:**
- ✅ Garantía matemática: sum(debits) = sum(credits)
- ✅ Transferencias son naturales (no requieren lógica especial)
- ✅ Generación automática de Balance Sheet, Income Statement
- ✅ Base para reconciliación automática

**ALTERNATIVA (MENOS INVASIVA):**
Mantener `Transaction` actual pero agregar validación de balance + tabla de `AccountLedger` con saldo running.

#### 2.0.2 Transaction Immutability
**IMPLEMENTAR:**
- ✅ Soft delete: agregar `deleted_at` column
- ✅ Audit trail: tabla `AuditLog` para tracking de cambios
- ✅ Voids/Reversals: en vez de DELETE, crear transacción inversa
- ✅ Estado `VOID` para transacciones canceladas

```python
class Transaction(Base):
    # ... existing fields
    deleted_at: Mapped[Optional[datetime]]
    voided_at: Mapped[Optional[datetime]]
    void_reason: Mapped[Optional[str]]
    voided_by_transaction_id: Mapped[Optional[UUID]]

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None and self.voided_at is None
```

#### 2.0.3 Reconciliation Entity
**IMPLEMENTAR:**
```python
class Reconciliation(Base):
    """Weekly/Monthly reconciliation per account"""
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"))
    reconciliation_date: Mapped[date]
    statement_balance: Mapped[Decimal]  # From bank statement
    system_balance: Mapped[Decimal]     # From our calculations
    difference: Mapped[Decimal]
    status: Mapped[ReconciliationStatus]  # PENDING, RECONCILED, DISCREPANCY
    notes: Mapped[Optional[str]]
    reconciled_by: Mapped[Optional[UUID]]
    reconciled_at: Mapped[Optional[datetime]]

    __table_args__ = (
        Index('idx_reconciliation_account_date', 'account_id', 'reconciliation_date'),
    )

class ReconciliationStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RECONCILED = "reconciled"
    DISCREPANCY = "discrepancy"
```

**ENDPOINT:**
```python
POST /api/v1/reconciliation
{
  "account_id": "uuid",
  "reconciliation_date": "2026-04-25",
  "statement_balance": 1500.00
}
# Response: { "difference": -15.50, "status": "discrepancy", "missing_transactions": [...] }
```

---

### FASE 1: Tarjetas de Crédito & Facturas (Semanas 3-4) 🟡 IMPORTANTE

#### 2.1.1 Credit Card Enhancements
**EXTENDER `Account` model:**
```python
class Account(Base):
    # ... existing fields

    # Credit Card specific fields
    credit_limit: Mapped[Optional[Decimal]]  # Línea de crédito
    available_credit: Mapped[Optional[Decimal]]  # credit_limit - current_balance
    billing_cycle_day: Mapped[Optional[int]]  # Día de corte (1-31)
    payment_due_day: Mapped[Optional[int]]  # Día de pago (1-31)
    minimum_payment_percentage: Mapped[Optional[Decimal]]  # % de pago mínimo
    interest_rate: Mapped[Optional[Decimal]]  # APR/TEA
    grace_period_days: Mapped[Optional[int]] = mapped_column(default=21)

    @property
    def utilization_rate(self) -> Optional[Decimal]:
        """Credit utilization % (important for credit score)"""
        if self.account_type == AccountType.CREDIT_CARD and self.credit_limit:
            return (self.current_balance / self.credit_limit) * 100
        return None

    def calculate_minimum_payment(self) -> Decimal:
        """Calculate minimum payment for current balance"""
        if self.account_type == AccountType.CREDIT_CARD:
            return self.current_balance * (self.minimum_payment_percentage / 100)
        return Decimal("0")
```

**NUEVA ENTIDAD: Credit Card Statement**
```python
class CreditCardStatement(Base):
    """Monthly credit card statements"""
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"))
    statement_date: Mapped[date]  # Billing cycle close date
    due_date: Mapped[date]        # Payment due date
    previous_balance: Mapped[Decimal]
    payments_made: Mapped[Decimal]
    purchases: Mapped[Decimal]
    interest_charged: Mapped[Decimal]
    fees_charged: Mapped[Decimal]
    closing_balance: Mapped[Decimal]
    minimum_payment: Mapped[Decimal]
    is_paid: Mapped[bool] = mapped_column(default=False)
    payment_date: Mapped[Optional[date]]
    payment_amount: Mapped[Optional[Decimal]]

    __table_args__ = (
        Index('idx_statement_account_date', 'account_id', 'statement_date'),
    )
```

**ENDPOINTS:**
```python
POST /api/v1/credit-cards/{account_id}/statements
GET  /api/v1/credit-cards/{account_id}/statements?start_date=...&end_date=...
GET  /api/v1/credit-cards/{account_id}/payment-due  # Next payment info
POST /api/v1/credit-cards/{account_id}/pay-statement
```

#### 2.1.2 Bills & Invoices Entity
**NUEVA ENTIDAD:**
```python
class Bill(Base):
    """Recurring bills (utilities, rent, subscriptions)"""
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]  # "Netflix", "Electricity", "Rent"
    merchant_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("merchants.id"))
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"))
    bill_type: Mapped[BillType]  # UTILITY, SUBSCRIPTION, RENT, INSURANCE, OTHER
    frequency: Mapped[Frequency]  # MONTHLY, QUARTERLY, YEARLY

    # Amount info
    is_fixed_amount: Mapped[bool]  # True for Netflix, False for electricity
    fixed_amount: Mapped[Optional[Decimal]]
    average_amount: Mapped[Optional[Decimal]]  # For variable bills

    # Due date info
    due_day: Mapped[int]  # Day of month (1-31)
    reminder_days_before: Mapped[int] = mapped_column(default=3)

    # Payment tracking
    auto_pay_enabled: Mapped[bool] = mapped_column(default=False)
    payment_account_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("accounts.id"))

    # Metadata
    reference_number: Mapped[Optional[str]]  # Account number, contract #
    notes: Mapped[Optional[str]]
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    occurrences: Mapped[List["BillOccurrence"]] = relationship()

class BillOccurrence(Base):
    """Individual bill instances"""
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bill_id: Mapped[UUID] = mapped_column(ForeignKey("bills.id"))
    due_date: Mapped[date]
    amount: Mapped[Optional[Decimal]]
    status: Mapped[BillStatus]  # PENDING, PAID, OVERDUE, CANCELLED
    paid_date: Mapped[Optional[date]]
    transaction_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("transactions.id"))

    __table_args__ = (
        Index('idx_bill_occurrence_due_date', 'due_date'),
        Index('idx_bill_occurrence_status', 'status'),
    )

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
```

**ENDPOINTS:**
```python
POST /api/v1/bills                    # Create recurring bill
GET  /api/v1/bills?status=active      # List bills
GET  /api/v1/bills/upcoming?days=30   # Bills due in next 30 days
POST /api/v1/bills/{bill_id}/pay      # Mark occurrence as paid
GET  /api/v1/bills/overdue            # Alert: overdue bills
```

---

### FASE 2: Multi-Currency & Analytics (Semanas 5-6) 🟡 IMPORTANTE

#### 2.2.1 Exchange Rates Tracking
**NUEVA ENTIDAD:**
```python
class ExchangeRate(Base):
    """Historical exchange rates"""
    id: Mapped[int] = mapped_column(primary_key=True)
    from_currency: Mapped[str] = mapped_column(String(3))
    to_currency: Mapped[str] = mapped_column(String(3))
    rate: Mapped[Decimal]
    rate_date: Mapped[date]
    source: Mapped[str]  # "manual", "API", "ECB", etc.
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        UniqueConstraint('from_currency', 'to_currency', 'rate_date'),
        Index('idx_fx_rate_currencies_date', 'from_currency', 'to_currency', 'rate_date'),
    )
```

**EXTENDER Transaction:**
```python
class Transaction(Base):
    # ... existing fields
    currency: Mapped[str] = mapped_column(String(3), default="COP")
    amount: Mapped[Decimal]  # Amount in original currency

    # NEW FIELDS:
    fx_rate: Mapped[Optional[Decimal]]  # Exchange rate applied
    base_currency: Mapped[str] = mapped_column(String(3))  # User's base currency
    base_amount: Mapped[Decimal]  # Amount converted to base currency
```

**ENDPOINT:**
```python
POST /api/v1/exchange-rates          # Manual entry
GET  /api/v1/exchange-rates/latest   # Latest rates
GET  /api/v1/exchange-rates/{from_currency}/{to_currency}?date=2026-04-25
POST /api/v1/exchange-rates/sync     # Fetch from external API
```

#### 2.2.2 Merchant Normalization
**NUEVA ENTIDAD:**
```python
class Merchant(Base):
    """Merchants/Vendors normalization"""
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]  # Normalized name: "Starbucks"
    aliases: Mapped[List[str]]  # ["STARBUCKS #123", "Starbucks Corp"]
    default_category_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("categories.id"))
    logo_url: Mapped[Optional[str]]
    is_recurring: Mapped[bool] = mapped_column(default=False)
    website: Mapped[Optional[str]]

    __table_args__ = (
        UniqueConstraint('user_id', 'name'),
    )
```

**EXTENDER Transaction:**
```python
class Transaction(Base):
    # ... existing fields
    merchant_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("merchants.id"))
    payment_method: Mapped[Optional[PaymentMethod]]  # NEW

class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    DEBIT_CARD = "debit_card"
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    MOBILE_WALLET = "mobile_wallet"  # Nequi, Daviplata
    CHECK = "check"
    OTHER = "other"
```

#### 2.2.3 Split Transactions
**NUEVA ENTIDAD:**
```python
class TransactionSplit(Base):
    """Split a transaction across multiple categories"""
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[UUID] = mapped_column(ForeignKey("transactions.id"))
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"))
    amount: Mapped[Decimal]
    description: Mapped[Optional[str]]

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_split_amount_positive"),
    )

# Constraint: sum(splits.amount) MUST EQUAL transaction.amount
@validates_constraint
def validate_split_sum(mapper, connection, target):
    splits = session.query(TransactionSplit).filter_by(transaction_id=target.transaction_id).all()
    total = sum(split.amount for split in splits)
    if total != target.transaction.amount:
        raise ValueError(f"Split sum ({total}) != transaction amount ({target.transaction.amount})")
```

---

### FASE 3: Advanced Features (Semanas 7-8) 🟢 NICE-TO-HAVE

#### 2.3.1 Auto-Categorization Rules
**NUEVA ENTIDAD:**
```python
class CategorizationRule(Base):
    """Rules for auto-categorizing transactions"""
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    priority: Mapped[int] = mapped_column(default=1)  # Higher = applied first

    # Match conditions (JSONB for flexibility)
    conditions: Mapped[dict]  # {"description_contains": "NETFLIX", "amount_gte": 15}

    # Actions
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"))
    merchant_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("merchants.id"))
    tags_to_add: Mapped[List[UUID]]

    is_active: Mapped[bool] = mapped_column(default=True)
```

#### 2.3.2 Debt Amortization Schedule
**EXTENDER Debt:**
```python
class Debt(Base):
    # ... existing fields
    payment_frequency: Mapped[Optional[Frequency]]  # MONTHLY, BIWEEKLY
    scheduled_payment_amount: Mapped[Optional[Decimal]]
    next_payment_date: Mapped[Optional[date]]
    total_installments: Mapped[Optional[int]]
    current_installment: Mapped[int] = mapped_column(default=0)

class DebtAmortizationSchedule(Base):
    """Amortization table for installment loans"""
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    debt_id: Mapped[UUID] = mapped_column(ForeignKey("debts.id"))
    installment_number: Mapped[int]
    due_date: Mapped[date]
    opening_balance: Mapped[Decimal]
    scheduled_payment: Mapped[Decimal]
    principal_component: Mapped[Decimal]
    interest_component: Mapped[Decimal]
    closing_balance: Mapped[Decimal]
    status: Mapped[PaymentStatus]  # SCHEDULED, PAID, OVERDUE
```

#### 2.3.3 Investment Portfolio Tracking
**EXTENDER Investment:**
```python
class Investment(Base):
    # ... existing fields
    ticker_symbol: Mapped[Optional[str]]  # "BTC", "AAPL"
    units: Mapped[Decimal] = mapped_column(default=Decimal("0"))  # Shares/coins
    cost_basis: Mapped[Decimal]  # Average cost per unit
    unrealized_gain_loss: Mapped[Decimal]  # current_value - (units * cost_basis)

    @property
    def realized_gain_loss(self) -> Decimal:
        """From completed sales"""
        return sum(m.amount for m in self.movements if m.movement_type == MovementType.WITHDRAWAL)
```

---

### FASE 4: Motor de Diagnóstico Mensual (Semanas Especiales)

#### 2.4.1 Monthly Close Service
**NUEVA ENTIDAD:**
```python
class MonthlyClose(Base):
    """Monthly financial diagnosis snapshot"""
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    year: Mapped[int]
    month: Mapped[int]
    close_date: Mapped[date]

    # Summary metrics
    total_income: Mapped[Decimal]
    total_expense: Mapped[Decimal]
    net_savings: Mapped[Decimal]
    savings_rate: Mapped[Decimal]  # % of income saved

    # Comparison
    income_vs_last_month: Mapped[Decimal]  # % change
    expense_vs_last_month: Mapped[Decimal]
    expense_vs_3month_avg: Mapped[Decimal]

    # Breakdown
    fixed_expenses: Mapped[Decimal]
    variable_expenses: Mapped[Decimal]
    financial_cost: Mapped[Decimal]  # Interest paid on debts

    # Quality indicators
    uncategorized_transactions_count: Mapped[int]
    unreconciled_accounts_count: Mapped[int]
    data_quality_score: Mapped[Decimal]  # 0-100

    # Top drivers (JSONB)
    top_expense_categories: Mapped[dict]  # [{"category": "Food", "amount": 500, "pct": 25}]
    top_merchants: Mapped[dict]
    top_payment_methods: Mapped[dict]

    # Insights & recommendations
    insights: Mapped[List[dict]]  # [{"type": "overspending", "category": "Restaurants", ...}]
    recommendations: Mapped[List[dict]]

    status: Mapped[CloseStatus]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

class CloseStatus(str, enum.Enum):
    DRAFT = "draft"
    FINAL = "final"
    UNRELIABLE = "unreliable"  # Due to reconciliation issues
```

**SERVICE:**
```python
class MonthlyCloseService:
    def execute_close(self, user_id: UUID, year: int, month: int) -> MonthlyClose:
        """Execute monthly financial close"""
        # 1. Validate reconciliations
        # 2. Calculate all metrics
        # 3. Identify top drivers
        # 4. Generate insights
        # 5. Persist snapshot
        # 6. Return MonthlyClose object

    def generate_insights(self, user_id: UUID, year: int, month: int) -> List[Insight]:
        """Generate actionable insights"""
        insights = []

        # Example insights:
        # - "Spending on Restaurants increased 40% vs last month"
        # - "You're on track to exceed budget in Transportation by 15%"
        # - "Credit card utilization is 85% - consider paying down balance"
        # - "3 bills are overdue totaling $125"

        return insights
```

**ENDPOINTS:**
```python
POST /api/v1/monthly-close/{user_id}?year=2026&month=4
  # Execute close, returns MonthlyClose object

GET  /api/v1/monthly-close/{user_id}?year=2026&month=4
  # Retrieve close report

GET  /api/v1/insights/{user_id}?start_date=...&end_date=...
  # Get insights for period

GET  /api/v1/financial-health/{user_id}
  # Current financial health dashboard
```

#### 2.4.2 Budget Monitoring Enhancements
**EXTENDER BudgetProgress:**
```python
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

    # NEW FIELDS:
    projected_overspend: Optional[Decimal]  # Based on current pace
    alert_level: AlertLevel  # NONE, WARNING (80%), CRITICAL (100%), EXCEEDED
    days_left_in_period: int
    daily_budget_remaining: Decimal

class AlertLevel(str, enum.Enum):
    NONE = "none"
    WARNING = "warning"      # 80-99%
    CRITICAL = "critical"    # 100-109%
    EXCEEDED = "exceeded"    # 110%+
```

#### 2.4.3 Financial Health Dashboard
**ENDPOINT:**
```python
GET /api/v1/financial-health/{user_id}
{
  "net_worth": {
    "total_assets": 50000,
    "total_liabilities": 15000,
    "net_worth": 35000
  },
  "cash_flow": {
    "monthly_income_avg": 5000,
    "monthly_expense_avg": 3500,
    "monthly_net_avg": 1500,
    "savings_rate": 30  # %
  },
  "debt_summary": {
    "total_debt": 15000,
    "total_monthly_payments": 500,
    "debt_to_income_ratio": 10,  # %
    "total_interest_this_month": 150
  },
  "credit_cards": {
    "total_balance": 2000,
    "total_limit": 10000,
    "utilization_rate": 20,  # %
    "upcoming_payments": [
      {"card": "Visa", "due_date": "2026-05-05", "minimum": 50, "total": 2000}
    ]
  },
  "bills": {
    "upcoming_30days": 5,
    "overdue": 0,
    "total_monthly_bills": 800
  },
  "alerts": [
    {"type": "budget_exceeded", "category": "Dining", "severity": "critical"},
    {"type": "bill_due_soon", "bill": "Internet", "days": 3},
    {"type": "high_credit_utilization", "card": "Visa", "rate": 85}
  ]
}
```

---

### FASE 5: Dashboard & Reports (Post-MVP)

---

## 3. Resumen de APIs Nuevas

### 3.1 Double-Entry & Accounting
```
POST   /api/v1/journal-entries              # Create journal entry
GET    /api/v1/journal-entries               # List entries
POST   /api/v1/journal-entries/{id}/post     # Post (finalize) entry
POST   /api/v1/journal-entries/{id}/void     # Void entry

GET    /api/v1/accounts/{id}/ledger          # Account ledger (running balance)
GET    /api/v1/reports/balance-sheet         # Balance sheet report
GET    /api/v1/reports/income-statement      # P&L statement
```

### 3.2 Reconciliation
```
POST   /api/v1/reconciliation                # Start reconciliation
GET    /api/v1/reconciliation/{account_id}   # Reconciliation history
PUT    /api/v1/reconciliation/{id}/complete  # Mark as reconciled
GET    /api/v1/reconciliation/status         # Status by account
```

### 3.3 Credit Cards
```
GET    /api/v1/credit-cards                  # List credit card accounts
POST   /api/v1/credit-cards/{id}/statements  # Create statement
GET    /api/v1/credit-cards/{id}/statements  # Statement history
GET    /api/v1/credit-cards/{id}/payment-due # Next payment info
POST   /api/v1/credit-cards/{id}/pay         # Record payment
GET    /api/v1/credit-cards/utilization      # Utilization summary
```

### 3.4 Bills & Invoices
```
POST   /api/v1/bills                         # Create recurring bill
GET    /api/v1/bills                         # List bills
GET    /api/v1/bills/upcoming?days=30        # Bills due soon
GET    /api/v1/bills/overdue                 # Overdue bills
POST   /api/v1/bills/{id}/occurrences        # Create occurrence
POST   /api/v1/bills/{id}/pay                # Mark as paid
```

### 3.5 Multi-Currency
```
POST   /api/v1/exchange-rates                # Add rate
GET    /api/v1/exchange-rates/latest         # Latest rates
GET    /api/v1/exchange-rates/{from}/{to}    # Rate for pair
POST   /api/v1/exchange-rates/sync           # Sync from external API
```

### 3.6 Merchants & Categories
```
POST   /api/v1/merchants                     # Create merchant
GET    /api/v1/merchants                     # List merchants
PUT    /api/v1/merchants/{id}/merge          # Merge duplicates
GET    /api/v1/merchants/top?period=30d      # Top merchants by spending
```

### 3.7 Split Transactions
```
POST   /api/v1/transactions/{id}/splits      # Add split
GET    /api/v1/transactions/{id}/splits      # Get splits
PUT    /api/v1/transactions/{id}/splits      # Update splits
```

### 3.8 Monthly Close & Insights
```
POST   /api/v1/monthly-close?year=YYYY&month=MM  # Execute close
GET    /api/v1/monthly-close?year=YYYY&month=MM  # Get close report
GET    /api/v1/insights?start_date=...&end_date=... # Insights
GET    /api/v1/financial-health              # Financial health dashboard
```

### 3.9 Auto-Categorization
```
POST   /api/v1/categorization-rules          # Create rule
GET    /api/v1/categorization-rules           # List rules
POST   /api/v1/transactions/auto-categorize  # Apply rules to uncategorized
```

### 3.10 Ajustes a Endpoints Existentes
```
# Transactions
POST   /api/v1/transactions
  # NEW FIELDS: merchant_id, payment_method, fx_rate, base_amount

PUT    /api/v1/transactions/{id}
  # DEPRECADO: Usar soft delete o void

DELETE /api/v1/transactions/{id}
  # CAMBIO: Soft delete (set deleted_at), no hard delete

# Budgets
GET    /api/v1/budgets/{id}/progress
  # NEW FIELDS: projected_overspend, alert_level, days_left

# Accounts
GET    /api/v1/accounts/{id}
  # NEW FIELDS (credit cards): credit_limit, available_credit,
  #             billing_cycle_day, payment_due_day, utilization_rate
```

---

## 4. Estrategia de Migración de Datos

### 4.1 Opción A: Mantener Tabla `Transaction` Actual + Mejoras
**PROS:**
- ✅ Menos refactoring
- ✅ Rollout más rápido
- ✅ Backward compatible

**CONS:**
- ❌ No es "true accounting"
- ❌ Balances no garantizados matemáticamente
- ❌ Dificulta reportes contables estándar

**APPROACH:**
1. Agregar campos a `Transaction`: `fx_rate`, `base_amount`, `merchant_id`, `payment_method`
2. Crear tablas complementarias: `Reconciliation`, `Bill`, `CreditCardStatement`, `Merchant`, `ExchangeRate`
3. Agregar tabla `TransactionSplit` para splits
4. Implementar soft delete (agregar `deleted_at`, `voided_at`)
5. Crear views para reportes (simular double-entry)

### 4.2 Opción B: Migrar a Double-Entry (RECOMENDADO) ✅
**PROS:**
- ✅ Fundamento contable sólido
- ✅ Garantía matemática de balance
- ✅ Reconciliación automática
- ✅ Escalable a largo plazo

**CONS:**
- ❌ Refactoring significativo
- ❌ Migración de datos existentes compleja
- ❌ Mayor tiempo de desarrollo inicial

**APPROACH:**
1. Crear nuevas tablas: `JournalEntry`, `JournalEntryLine`
2. Mantener `Transaction` como vista o deprecated
3. Script de migración:
   ```python
   for tx in Transaction.all():
       entry = JournalEntry(date=tx.date, description=tx.description)
       if tx.type == INCOME:
           entry.add_line(debit=tx.account_id, amount=tx.amount)
           entry.add_line(credit=income_account_id, amount=tx.amount)
       elif tx.type == EXPENSE:
           entry.add_line(debit=expense_account_id, amount=tx.amount)
           entry.add_line(credit=tx.account_id, amount=tx.amount)
       entry.post()
   ```
4. Validar: sum(debits) == sum(credits) para todos los entries
5. Deprecar endpoints de `Transaction`, migrar a `JournalEntry`

**RECOMENDACIÓN:** **Opción B** si el proyecto es de largo plazo y necesitas compliance contable.

---

## 5. Pruebas y Criterios de Aceptación

### 5.1 Unit Tests Críticos
```python
def test_journal_entry_must_balance():
    """Double-entry: sum(debits) = sum(credits)"""
    entry = create_journal_entry([
        {"account": cash_account, "debit": 100},
        {"account": income_account, "credit": 100}
    ])
    assert entry.is_balanced() == True
    assert entry.can_post() == True

def test_account_balance_integrity():
    """Account balance = initial + transactions"""
    account = Account(initial_balance=1000)
    create_income(account, 500)   # +500
    create_expense(account, 200)  # -200
    assert account.current_balance == 1300

def test_transfer_does_not_affect_net_worth():
    """Transfer between accounts is net-zero"""
    net_worth_before = calculate_net_worth(user)
    create_transfer(from_account, to_account, 100)
    net_worth_after = calculate_net_worth(user)
    assert net_worth_before == net_worth_after

def test_credit_card_payment_reduces_balance():
    """Paying credit card reduces balance"""
    card = CreditCard(current_balance=1000)
    create_payment(card, 500)
    assert card.current_balance == 500

def test_split_transaction_sum_equals_total():
    """Split amounts must equal transaction total"""
    tx = Transaction(amount=100)
    tx.add_split(category_A, 60)
    tx.add_split(category_B, 30)
    tx.add_split(category_C, 10)
    assert sum(tx.splits) == tx.amount

def test_reconciliation_detects_discrepancy():
    """Reconciliation finds missing transactions"""
    account.system_balance = 1000
    reconciliation = Reconciliation(account, statement_balance=1050)
    assert reconciliation.difference == -50  # Missing $50 income

def test_budget_alert_at_80_percent():
    """Budget alert triggers at 80%"""
    budget = Budget(amount=1000)
    spend_on_category(800)
    progress = budget.get_progress()
    assert progress.alert_level == AlertLevel.WARNING

def test_bill_marked_overdue_after_due_date():
    """Bill status changes to OVERDUE after due date"""
    bill = BillOccurrence(due_date=date(2026, 4, 1))
    # Current date: 2026-04-10
    assert bill.status == BillStatus.OVERDUE

def test_fx_rate_persisted_in_transaction():
    """Multi-currency transaction stores FX rate"""
    tx = create_transaction(amount=100, currency="USD")
    assert tx.fx_rate is not None
    assert tx.base_amount == 100 * tx.fx_rate  # Converted to COP

def test_transaction_immutability():
    """Transactions cannot be edited after posting"""
    tx = create_transaction(...)
    tx.post()
    with pytest.raises(ValidationError):
        tx.amount = 200  # Should fail

def test_soft_delete_preserves_data():
    """Deleted transactions remain in database"""
    tx = create_transaction(...)
    tx.delete()  # Soft delete
    assert tx.deleted_at is not None
    assert Transaction.query.get(tx.id) is not None  # Still exists

def test_merchant_auto_categorization():
    """Merchant triggers auto-categorization"""
    rule = CategorizationRule(
        merchant_name_contains="STARBUCKS",
        category=coffee_category
    )
    tx = create_transaction(description="STARBUCKS #123", merchant=None)
    apply_categorization_rules(tx)
    assert tx.category_id == coffee_category.id
```

### 5.2 Integration Tests
```python
def test_monthly_close_end_to_end():
    """Monthly close calculates all metrics correctly"""
    # Setup: Create income, expenses, bills, credit card transactions
    create_income(1000)
    create_expense(600)
    create_bill_payment(200)
    create_credit_card_interest(50)

    # Execute close
    close = execute_monthly_close(user, year=2026, month=4)

    # Assertions
    assert close.total_income == 1000
    assert close.total_expense == 600
    assert close.net_savings == 400
    assert close.savings_rate == 40  # %
    assert close.financial_cost == 50
    assert len(close.top_expense_categories) == 3
    assert close.status == CloseStatus.FINAL

def test_credit_card_statement_generation():
    """Credit card statement calculates correctly"""
    card = CreditCard(
        billing_cycle_day=1,
        payment_due_day=25,
        previous_balance=1000
    )
    create_purchase(card, 500, date(2026, 4, 5))
    create_purchase(card, 300, date(2026, 4, 10))
    create_payment(card, 1000, date(2026, 4, 20))

    statement = generate_statement(card, month=4)

    assert statement.previous_balance == 1000
    assert statement.purchases == 800
    assert statement.payments_made == 1000
    assert statement.closing_balance == 800
    assert statement.due_date == date(2026, 5, 25)
```

### 5.3 Criterios de Aceptación del MVP

#### Data Integrity ✅
- [ ] Todas las transacciones balancean (si double-entry)
- [ ] Balances de cuentas coinciden con suma de transacciones
- [ ] Transferencias son net-zero para net worth
- [ ] Multi-currency: todas las transacciones tienen `fx_rate` y `base_amount`
- [ ] Reconciliaciones semanales completadas sin discrepancias > 1%

#### Features ✅
- [ ] Usuario puede crear transacciones con splits
- [ ] Tarjetas de crédito muestran billing cycle, due date, utilization
- [ ] Bills recurrentes generan occurrences automáticamente
- [ ] Overdue bills aparecen en alertas
- [ ] Budgets muestran alert level (warning, critical, exceeded)
- [ ] Merchants se normalizan (no duplicados "Starbucks" vs "STARBUCKS")
- [ ] Auto-categorization rules funcionan

#### Reports ✅
- [ ] Monthly close genera diagnóstico completo
- [ ] Top 3 expense drivers son correctos (category, merchant, payment method)
- [ ] Financial health dashboard muestra métricas clave
- [ ] Balance sheet balancea (Assets = Liabilities + Equity)
- [ ] Income statement separa operating vs financial expenses

#### UX ✅
- [ ] Dashboard responde "¿dónde se fue mi dinero?" claramente
- [ ] Drill-down: summary → category → merchant → transactions funciona
- [ ] Alertas son accionables (no solo informativas)
- [ ] Usuario entiende próximos vencimientos (bills, credit cards)

---

## 6. Supuestos y Decisiones de Diseño

### 6.1 Supuestos del MVP
- ✅ **Single-user:** No multi-tenant (un usuario = una instancia)
- ✅ **Manual data entry:** Integraciones bancarias en Fase 2
- ✅ **Moneda base única:** Usuario elige su moneda principal (ej: COP)
- ✅ **Reconciliación semanal:** Requerida para data quality
- ✅ **Categorías predefinidas:** Seed categories on user creation
- ✅ **Sin forecasting:** Diagnóstico retroactivo, no predictivo (MVP)

### 6.2 Decisiones Técnicas
- ✅ **PostgreSQL:** JSONB para metadata flexible
- ✅ **SQLAlchemy 2.0:** Migrar a `Mapped[T]` syntax (Fase 3)
- ✅ **UUIDs:** Primary keys para APIs distribuidas
- ✅ **Soft delete:** `deleted_at` en vez de hard delete
- ✅ **Audit trail:** Tabla `AuditLog` para compliance
- ✅ **Indexes:** Compuestos en queries frecuentes
- ✅ **Constraints:** CheckConstraints a nivel de BD
- ✅ **Cascade:** `delete-orphan` para integridad referencial

### 6.3 Out of Scope (Post-MVP)
- ❌ Multi-user / Family accounts
- ❌ Bank sync / Plaid integration
- ❌ Mobile apps (solo API)
- ❌ AI/ML predictions
- ❌ Tax reports
- ❌ Payroll management
- ❌ Business accounting

---

## 7. Recursos y Referencias

### 7.1 Documentación Técnica Consultada
- **Double-Entry Accounting:**
  - [Journalize.io - Elegant DB Schema](https://blog.journalize.io/posts/an-elegant-db-schema-for-double-entry-accounting/)
  - [TigerBeetle - Debit/Credit Schema](https://docs.tigerbeetle.com/concepts/debit-credit/)
  - [Square Books - Immutable Accounting](https://developer.squareup.com/blog/books-an-immutable-double-entry-accounting-database-service/)

- **SQLAlchemy:**
  - [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
  - [Mapped Column Type Hints](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html)

- **Personal Finance Apps:**
  - [Firefly III](https://www.firefly-iii.org/) - Open source, double-entry
  - [Actual Budget](https://actualbudget.org/) - Privacy-first, envelope budgeting
  - [YNAB](https://www.ynab.com) - Zero-based budgeting
  - [Feature Comparison](https://ezbookkeeping.mayswind.net/comparison/)

- **Credit Cards:**
  - [Chase - Billing Cycles Explained](https://www.chase.com/personal/credit-cards/education/basics/credit-card-billing-cycles-explained)
  - [Urban Money - Billing Cycle Guide](https://www.urbanmoney.com/credit-card/credit-card-billing-cycle)

### 7.2 Próximos Pasos

1. **Revisar ANALISIS_TECNICO.md** - Análisis completo de gaps y mejoras
2. **Decidir:** Opción A (mejoras incrementales) vs Opción B (double-entry completo)
3. **Priorizar:** Revisar FASE 0-4, ajustar según recursos
4. **Implementar:** Seguir orden de prioridad (🔴 Crítico → 🟡 Importante → 🟢 Nice-to-have)
5. **Testing:** Implementar tests críticos de la sección 5.1
6. **Deploy:** Usar Docker Compose para entorno local/staging
7. **Iterar:** Feedback de usuario → Ajustar plan

---

**Fin del Plan 2.0** - Ver `ANALISIS_TECNICO.md` para detalles de implementación específicos por entidad.
