# FinanzApp - Personal Finance Management API

A comprehensive microservice for managing personal finances built with FastAPI, PostgreSQL, and SQLAlchemy 2.0.

## Features

### Core Entities
- **Users** - User management with currency and timezone preferences
- **Accounts** - Multiple account types (checking, savings, credit card, cash, investment, wallet)
- **Categories** - Hierarchical income/expense categories
- **Transactions** - Complete transaction tracking with account balance updates
- **Recurring Transactions** - Automated recurring income/expenses
- **Budgets** - Category-based budgets with progress tracking
- **Financial Goals** - Savings goals with contribution tracking
- **Tags** - Flexible transaction tagging system
- **Attachments** - File attachments for transactions (receipts, invoices)

### Key Capabilities
- ✅ Multi-account support
- ✅ Transaction categorization
- ✅ Account balance tracking
- ✅ Transfer between accounts
- ✅ Budget monitoring with overspending alerts
- ✅ Financial goal tracking with progress estimation
- ✅ Recurring transaction templates
- ✅ File attachment management
- ✅ Transaction tagging
- ✅ Summary reports and analytics

## Tech Stack

- **Framework:** FastAPI 0.115.0
- **Database:** PostgreSQL 15
- **ORM:** SQLAlchemy 2.0.23
- **Migrations:** Alembic 1.12.1
- **Validation:** Pydantic 2.10.2
- **Server:** Uvicorn 0.32.0
- **Containerization:** Docker & Docker Compose

## Project Structure

```
finanzapp/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI application
│   ├── config.py                    # Settings with Pydantic
│   ├── database.py                  # SQLAlchemy setup
│   ├── models/
│   │   ├── db_models.py             # SQLAlchemy ORM models
│   │   └── schemas.py               # Pydantic schemas
│   ├── api/
│   │   ├── dependencies.py          # Dependency injection
│   │   └── v1/
│   │       ├── users.py
│   │       ├── accounts.py
│   │       ├── categories.py
│   │       ├── transactions.py
│   │       ├── recurring.py
│   │       ├── budgets.py
│   │       ├── goals.py
│   │       ├── tags.py
│   │       └── attachments.py
│   └── services/
│       ├── transaction_service.py   # Business logic
│       ├── budget_service.py
│       └── goal_service.py
├── alembic/                         # Database migrations
├── uploads/                         # File attachments
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── Makefile
└── README.md
```

## Database Schema

### Tables
1. **users** - User accounts
2. **accounts** - Financial accounts
3. **categories** - Income/expense categories (hierarchical)
4. **transactions** - All financial transactions
5. **recurring_transactions** - Recurring transaction templates
6. **budgets** - Budget definitions
7. **financial_goals** - Savings goals
8. **transaction_attachments** - File attachments
9. **tags** - Custom tags
10. **transaction_tags** - Many-to-many relationship

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Installation

1. Clone the repository:
```bash
cd /home/ubuntu/n8n/Micro-Services/finanzapp
```

2. Create environment file:
```bash
cp .env.example .env
```

3. Start the services:
```bash
make up
# or
docker-compose up -d
```

4. Run database migrations:
```bash
make migrate-auto message="Initial schema"
make migrate-upgrade
```

5. Access the API:
- API: http://localhost:5050
- Docs: http://localhost:5050/docs
- Health: http://localhost:5050/api/v1/health

## Makefile Commands

```bash
make help              # Show all commands
make build             # Build Docker containers
make up                # Start all services
make down              # Stop all services
make restart           # Restart all services
make logs              # View logs
make shell             # Access API container shell
make db-shell          # Access PostgreSQL shell
make migrate-auto      # Auto-generate migration
make migrate-upgrade   # Apply migrations
make migrate-downgrade # Rollback migration
make clean             # Remove containers and volumes
```

## API Endpoints

### Users
- `POST /api/v1/users` - Create user
- `GET /api/v1/users/{user_id}` - Get user
- `GET /api/v1/users` - List users
- `PUT /api/v1/users/{user_id}` - Update user
- `DELETE /api/v1/users/{user_id}` - Deactivate user

### Accounts
- `POST /api/v1/accounts` - Create account
- `GET /api/v1/accounts/{account_id}` - Get account
- `GET /api/v1/accounts` - List accounts
- `PUT /api/v1/accounts/{account_id}` - Update account
- `DELETE /api/v1/accounts/{account_id}` - Deactivate account
- `GET /api/v1/accounts/{account_id}/balance` - Get balance

### Categories
- `POST /api/v1/categories` - Create category
- `GET /api/v1/categories/{category_id}` - Get category
- `GET /api/v1/categories` - List categories
- `PUT /api/v1/categories/{category_id}` - Update category
- `DELETE /api/v1/categories/{category_id}` - Deactivate category

### Transactions
- `POST /api/v1/transactions` - Create transaction
- `POST /api/v1/transactions/transfer` - Create transfer
- `GET /api/v1/transactions/{transaction_id}` - Get transaction
- `GET /api/v1/transactions` - List transactions (with filters)
- `PUT /api/v1/transactions/{transaction_id}` - Update transaction
- `DELETE /api/v1/transactions/{transaction_id}` - Cancel transaction
- `GET /api/v1/transactions/summary/period` - Get summary
- `GET /api/v1/transactions/by-category/summary` - Group by category

### Recurring Transactions
- `POST /api/v1/recurring` - Create recurring transaction
- `GET /api/v1/recurring/{id}` - Get recurring transaction
- `GET /api/v1/recurring` - List recurring transactions
- `PUT /api/v1/recurring/{id}` - Update recurring transaction
- `DELETE /api/v1/recurring/{id}` - Deactivate recurring transaction
- `POST /api/v1/recurring/{id}/execute` - Execute manually

### Budgets
- `POST /api/v1/budgets` - Create budget
- `GET /api/v1/budgets/{id}` - Get budget
- `GET /api/v1/budgets` - List budgets
- `PUT /api/v1/budgets/{id}` - Update budget
- `DELETE /api/v1/budgets/{id}` - Delete budget
- `GET /api/v1/budgets/{id}/progress` - Get progress

### Financial Goals
- `POST /api/v1/goals` - Create goal
- `GET /api/v1/goals/{id}` - Get goal
- `GET /api/v1/goals` - List goals
- `PUT /api/v1/goals/{id}` - Update goal
- `DELETE /api/v1/goals/{id}` - Cancel goal
- `POST /api/v1/goals/{id}/contribute` - Add contribution
- `GET /api/v1/goals/{id}/progress` - Get progress

### Tags
- `POST /api/v1/tags` - Create tag
- `GET /api/v1/tags/{id}` - Get tag
- `GET /api/v1/tags` - List tags
- `PUT /api/v1/tags/{id}` - Update tag
- `DELETE /api/v1/tags/{id}` - Delete tag
- `POST /api/v1/tags/transactions/{transaction_id}/tags/{tag_id}` - Assign tag
- `DELETE /api/v1/tags/transactions/{transaction_id}/tags/{tag_id}` - Remove tag

### Attachments
- `POST /api/v1/attachments/transactions/{transaction_id}` - Upload file
- `GET /api/v1/attachments/transactions/{transaction_id}` - List attachments
- `GET /api/v1/attachments/{id}` - Download file
- `DELETE /api/v1/attachments/{id}` - Delete attachment

## Usage Examples

### 1. Create a User
```bash
curl -X POST http://localhost:5050/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "name": "John Doe",
    "currency": "COP",
    "timezone": "America/Bogota"
  }'
```

### 2. Create an Account
```bash
curl -X POST http://localhost:5050/api/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_UUID",
    "name": "Bancolombia Savings",
    "account_type": "savings",
    "institution": "Bancolombia",
    "currency": "COP",
    "initial_balance": 1000000
  }'
```

### 3. Create a Category
```bash
curl -X POST http://localhost:5050/api/v1/categories \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_UUID",
    "name": "Food & Dining",
    "type": "expense",
    "color": "#FF5733"
  }'
```

### 4. Create a Transaction
```bash
curl -X POST http://localhost:5050/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_UUID",
    "transaction_type": "expense",
    "amount": 50000,
    "account_id": "ACCOUNT_UUID",
    "category_id": "CATEGORY_UUID",
    "transaction_date": "2026-04-04",
    "description": "Grocery shopping"
  }'
```

### 5. Create a Budget
```bash
curl -X POST http://localhost:5050/api/v1/budgets \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_UUID",
    "category_id": "CATEGORY_UUID",
    "amount": 500000,
    "period_type": "monthly",
    "start_date": "2026-04-01",
    "end_date": "2026-04-30"
  }'
```

### 6. Create a Financial Goal
```bash
curl -X POST http://localhost:5050/api/v1/goals \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_UUID",
    "name": "Emergency Fund",
    "target_amount": 5000000,
    "target_date": "2026-12-31",
    "priority": 1
  }'
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `DB_HOST` - PostgreSQL host
- `DB_PORT` - PostgreSQL port
- `DB_NAME` - Database name
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password
- `API_HOST` - API server host
- `API_PORT` - API server port
- `UPLOAD_DIR` - Directory for file uploads
- `MAX_FILE_SIZE` - Maximum file size in MB

## Development

### Running Locally (without Docker)

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export DB_HOST=localhost
export DB_PORT=5432
# ... other variables
```

3. Run migrations:
```bash
alembic upgrade head
```

4. Start the server:
```bash
uvicorn app.main:app --reload
```

### Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback:
```bash
alembic downgrade -1
```

## Testing

Run tests (coming soon):
```bash
pytest
```

## Architecture Notes

### Transaction Flow
1. Client creates transaction via API
2. `transaction_service.create_transaction()` validates and creates transaction
3. Account balance is automatically updated
4. For transfers, two linked transactions are created

### Budget Monitoring
1. Budgets are defined for categories and time periods
2. `budget_service.get_budget_progress()` calculates spending
3. API returns percentage used and overspending status

### Goal Tracking
1. Goals track progress toward savings targets
2. `goal_service.contribute_to_goal()` updates current amount
3. Completion date is estimated based on contribution history

## Future Enhancements

- [ ] JWT Authentication
- [ ] Multi-user authentication
- [ ] CSV import/export
- [ ] PDF reports
- [ ] Email notifications for budget alerts
- [ ] Multi-currency with conversion rates
- [ ] Audit logging
- [ ] Scheduled execution of recurring transactions
- [ ] API webhooks
- [ ] Mobile app integration

## License

MIT License

## Support

For issues and questions, please open an issue on the repository.

## Version

Current version: 1.0.0
