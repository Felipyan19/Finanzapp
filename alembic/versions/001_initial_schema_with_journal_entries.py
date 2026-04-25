"""initial schema with journal entries

Revision ID: 001
Revises:
Create Date: 2026-04-25 15:48:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types
    op.execute("""
        CREATE TYPE accounttype AS ENUM ('bank', 'cash', 'credit_card', 'digital_wallet', 'investment', 'savings');
        CREATE TYPE categorytype AS ENUM ('income', 'expense');
        CREATE TYPE transactiontype AS ENUM ('income', 'expense', 'transfer', 'adjustment', 'debt_payment');
        CREATE TYPE transactionstatus AS ENUM ('pending', 'confirmed', 'completed', 'cancelled');
        CREATE TYPE transactionsource AS ENUM ('manual', 'whatsapp', 'telegram', 'n8n', 'import', 'recurring', 'api');
        CREATE TYPE frequency AS ENUM ('daily', 'weekly', 'biweekly', 'monthly', 'quarterly', 'yearly');
        CREATE TYPE periodtype AS ENUM ('weekly', 'monthly', 'quarterly', 'yearly');
        CREATE TYPE goalstatus AS ENUM ('active', 'completed', 'cancelled');
        CREATE TYPE debttype AS ENUM ('owed_by_me', 'owed_to_me');
        CREATE TYPE debtstatus AS ENUM ('active', 'paid', 'cancelled');
        CREATE TYPE investmenttype AS ENUM ('crypto', 'stocks', 'bonds', 'real_estate', 'mutual_funds', 'other');
        CREATE TYPE movementtype AS ENUM ('contribution', 'withdrawal', 'dividend', 'interest');
        CREATE TYPE entrystatus AS ENUM ('draft', 'posted', 'void');
        CREATE TYPE reconciliationstatus AS ENUM ('pending', 'in_progress', 'reconciled', 'discrepancy');
    """)

    # Users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='COP'),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='America/Bogota'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_users_email', 'users', ['email'])

    # Accounts table
    op.create_table('accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('account_type', sa.Enum('bank', 'cash', 'credit_card', 'digital_wallet', 'investment', 'savings', name='accounttype'), nullable=False),
        sa.Column('institution_name', sa.String(length=255)),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='COP'),
        sa.Column('initial_balance', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('current_balance', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        # Credit Card specific fields
        sa.Column('credit_limit', sa.Numeric(precision=15, scale=2)),
        sa.Column('available_credit', sa.Numeric(precision=15, scale=2)),
        sa.Column('billing_cycle_day', sa.Integer()),
        sa.Column('payment_due_day', sa.Integer()),
        sa.Column('minimum_payment_percentage', sa.Numeric(precision=5, scale=2)),
        sa.Column('interest_rate', sa.Numeric(precision=5, scale=2)),
        sa.Column('grace_period_days', sa.Integer(), server_default='21'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('initial_balance >= 0', name='check_initial_balance_positive'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_accounts_user_id', 'accounts', ['user_id'])

    # Categories table
    op.create_table('categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category_type', sa.Enum('income', 'expense', name='categorytype'), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True)),
        sa.Column('icon', sa.String(length=50)),
        sa.Column('color', sa.String(length=7)),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_user_category_name')
    )
    op.create_index('idx_categories_user_id', 'categories', ['user_id'])
    op.create_index('idx_categories_parent_id', 'categories', ['parent_id'])

    # Transactions table
    op.create_table('transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_type', sa.Enum('income', 'expense', 'transfer', 'adjustment', 'debt_payment', name='transactiontype'), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True)),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('description', sa.String(length=500)),
        sa.Column('notes', sa.Text()),
        sa.Column('status', sa.Enum('pending', 'confirmed', 'completed', 'cancelled', name='transactionstatus'), nullable=False, server_default='confirmed'),
        sa.Column('source', sa.Enum('manual', 'whatsapp', 'telegram', 'n8n', 'import', 'recurring', 'api', name='transactionsource'), nullable=False, server_default='manual'),
        sa.Column('counterparty_account_id', postgresql.UUID(as_uuid=True)),
        sa.Column('recurring_transaction_id', postgresql.UUID(as_uuid=True)),
        sa.Column('metadata', postgresql.JSONB()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('amount > 0', name='check_amount_positive'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['counterparty_account_id'], ['accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_transactions_user_id', 'transactions', ['user_id'])
    op.create_index('idx_transactions_account_id', 'transactions', ['account_id'])
    op.create_index('idx_transactions_date', 'transactions', ['transaction_date'])
    op.create_index('idx_transactions_user_date', 'transactions', ['user_id', 'transaction_date'])
    op.create_index('idx_transactions_category', 'transactions', ['category_id'])

    # Recurring Transactions table
    op.create_table('recurring_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True)),
        sa.Column('transaction_type', sa.Enum('income', 'expense', 'transfer', 'adjustment', 'debt_payment', name='transactiontype'), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('frequency', sa.Enum('daily', 'weekly', 'biweekly', 'monthly', 'quarterly', 'yearly', name='frequency'), nullable=False),
        sa.Column('interval_value', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date()),
        sa.Column('next_execution_date', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('auto_create', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('amount > 0', name='check_recurring_amount_positive'),
        sa.CheckConstraint('interval_value > 0', name='check_interval_positive'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_recurring_user_id', 'recurring_transactions', ['user_id'])
    op.create_index('idx_recurring_next_execution', 'recurring_transactions', ['next_execution_date'])

    # Budgets table
    op.create_table('budgets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('period_type', sa.Enum('weekly', 'monthly', 'quarterly', 'yearly', name='periodtype'), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('rollover', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('amount > 0', name='check_budget_amount_positive'),
        sa.CheckConstraint('end_date > start_date', name='check_budget_dates_valid'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_budgets_user_id', 'budgets', ['user_id'])
    op.create_index('idx_budgets_category_id', 'budgets', ['category_id'])

    # Financial Goals table
    op.create_table('financial_goals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True)),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('target_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('current_amount', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('target_date', sa.Date()),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.Enum('active', 'completed', 'cancelled', name='goalstatus'), nullable=False, server_default='active'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('target_amount > 0', name='check_target_amount_positive'),
        sa.CheckConstraint('current_amount >= 0', name='check_current_amount_non_negative'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_goals_user_id', 'financial_goals', ['user_id'])

    # Tags table
    op.create_table('tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('color', sa.String(length=7)),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_user_tag_name')
    )
    op.create_index('idx_tags_user_id', 'tags', ['user_id'])

    # Transaction Tags (many-to-many)
    op.create_table('transaction_tags',
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('transaction_id', 'tag_id')
    )

    # Transaction Attachments table
    op.create_table('transaction_attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_url', sa.String(length=500), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500)),
        sa.Column('mime_type', sa.String(length=100)),
        sa.Column('file_size', sa.Integer()),
        sa.Column('uploaded_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_attachments_transaction_id', 'transaction_attachments', ['transaction_id'])

    # Debts table
    op.create_table('debts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('debt_type', sa.Enum('owed_by_me', 'owed_to_me', name='debttype'), nullable=False),
        sa.Column('principal_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('current_balance', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('interest_rate', sa.Numeric(precision=5, scale=2)),
        sa.Column('lender_or_borrower', sa.String(length=255)),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='COP'),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date()),
        sa.Column('status', sa.Enum('active', 'paid', 'cancelled', name='debtstatus'), nullable=False, server_default='active'),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_debts_user_id', 'debts', ['user_id'])

    # Investments table
    op.create_table('investments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('investment_type', sa.Enum('crypto', 'stocks', 'bonds', 'real_estate', 'mutual_funds', 'other', name='investmenttype'), nullable=False),
        sa.Column('platform_name', sa.String(length=255)),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='COP'),
        sa.Column('initial_value', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('current_value', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_investments_user_id', 'investments', ['user_id'])

    # Investment Movements table
    op.create_table('investment_movements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('investment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True)),
        sa.Column('movement_type', sa.Enum('contribution', 'withdrawal', 'dividend', 'interest', name='movementtype'), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('movement_date', sa.Date(), nullable=False),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['investment_id'], ['investments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_investment_movements_investment_id', 'investment_movements', ['investment_id'])

    # ============================================================================
    # JOURNAL ENTRIES (DOUBLE-ENTRY BOOKKEEPING)
    # ============================================================================

    # Journal Entries table
    op.create_table('journal_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entry_number', sa.String(length=50)),
        sa.Column('entry_date', sa.Date(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('reference', sa.String(length=100)),
        sa.Column('status', sa.Enum('draft', 'posted', 'void', name='entrystatus'), nullable=False, server_default='draft'),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True)),
        sa.Column('posted_at', sa.TIMESTAMP()),
        sa.Column('voided_at', sa.TIMESTAMP()),
        sa.Column('void_reason', sa.Text()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_journal_entry_user_date', 'journal_entries', ['user_id', 'entry_date'])
    op.create_index('idx_journal_entry_status', 'journal_entries', ['status'])
    op.create_index('idx_journal_entry_transaction', 'journal_entries', ['transaction_id'])

    # Journal Entry Lines table
    op.create_table('journal_entry_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('journal_entry_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True)),
        sa.Column('debit_amount', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('credit_amount', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0'),
        sa.Column('description', sa.String(length=500)),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('(debit_amount > 0 AND credit_amount = 0) OR (debit_amount = 0 AND credit_amount > 0)', name='check_debit_or_credit_not_both'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['journal_entry_id'], ['journal_entries.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_journal_line_entry', 'journal_entry_lines', ['journal_entry_id'])
    op.create_index('idx_journal_line_account', 'journal_entry_lines', ['account_id'])

    # ============================================================================
    # RECONCILIATIONS
    # ============================================================================

    # Reconciliations table
    op.create_table('reconciliations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reconciliation_date', sa.Date(), nullable=False),
        sa.Column('statement_balance', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('system_balance', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('difference', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('status', sa.Enum('pending', 'in_progress', 'reconciled', 'discrepancy', name='reconciliationstatus'), nullable=False, server_default='pending'),
        sa.Column('notes', sa.Text()),
        sa.Column('reconciled_by', postgresql.UUID(as_uuid=True)),
        sa.Column('reconciled_at', sa.TIMESTAMP()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reconciled_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_reconciliation_account_date', 'reconciliations', ['account_id', 'reconciliation_date'])
    op.create_index('idx_reconciliation_status', 'reconciliations', ['status'])

def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('reconciliations')
    op.drop_table('journal_entry_lines')
    op.drop_table('journal_entries')
    op.drop_table('investment_movements')
    op.drop_table('investments')
    op.drop_table('debts')
    op.drop_table('transaction_attachments')
    op.drop_table('transaction_tags')
    op.drop_table('tags')
    op.drop_table('financial_goals')
    op.drop_table('budgets')
    op.drop_table('recurring_transactions')
    op.drop_table('transactions')
    op.drop_table('categories')
    op.drop_table('accounts')
    op.drop_table('users')

    # Drop ENUM types
    op.execute("""
        DROP TYPE IF EXISTS reconciliationstatus;
        DROP TYPE IF EXISTS entrystatus;
        DROP TYPE IF EXISTS movementtype;
        DROP TYPE IF EXISTS investmenttype;
        DROP TYPE IF EXISTS debtstatus;
        DROP TYPE IF EXISTS debttype;
        DROP TYPE IF EXISTS goalstatus;
        DROP TYPE IF EXISTS periodtype;
        DROP TYPE IF EXISTS frequency;
        DROP TYPE IF EXISTS transactionsource;
        DROP TYPE IF EXISTS transactionstatus;
        DROP TYPE IF EXISTS transactiontype;
        DROP TYPE IF EXISTS categorytype;
        DROP TYPE IF EXISTS accounttype;
    """)
