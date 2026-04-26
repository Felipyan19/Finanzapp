from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import sqlalchemy

from app.config import settings
from app.database import engine, get_db
from app.models import db_models, schemas

# Import routers
from app.api.endpoints import (
    auth,
    users,
    accounts,
    categories,
    transactions,
    recurring,
    budgets,
    goals,
    tags,
    attachments,
    journal_entries,
    reconciliations,
    bills,
    debts,
    fixed_transactions,
)

# Create database tables
db_models.Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Personal Finance Management API - Complete system for managing finances",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(accounts.router, prefix=settings.api_prefix)
app.include_router(categories.router, prefix=settings.api_prefix)
app.include_router(transactions.router, prefix=settings.api_prefix)
app.include_router(recurring.router, prefix=settings.api_prefix)
app.include_router(budgets.router, prefix=settings.api_prefix)
app.include_router(goals.router, prefix=settings.api_prefix)
app.include_router(tags.router, prefix=settings.api_prefix)
app.include_router(attachments.router, prefix=settings.api_prefix)
app.include_router(journal_entries.router, prefix=settings.api_prefix)
app.include_router(reconciliations.router, prefix=settings.api_prefix)
app.include_router(bills.router, prefix=settings.api_prefix)
app.include_router(debts.router, prefix=settings.api_prefix)
app.include_router(fixed_transactions.router, prefix=settings.api_prefix)


@app.get("/", tags=["root"])
def root():
    """Root endpoint"""
    return {
        "message": "Welcome to FinanzApp API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health"
    }


@app.get(f"{settings.api_prefix}/health", response_model=schemas.HealthCheckResponse, tags=["health"])
def health_check():
    """Health check endpoint"""
    # Check database connection
    try:
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return schemas.HealthCheckResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        database=db_status,
        version=settings.app_version,
        timestamp=datetime.now()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
