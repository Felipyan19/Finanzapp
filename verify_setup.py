#!/usr/bin/env python3
"""
Verification script to check if all modules can be imported successfully.
Run this before starting the application to catch any import errors.
"""

import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

def verify_imports():
    """Verify all critical imports work"""
    errors = []

    try:
        print("Checking config...")
        from app.config import settings
        print(f"✓ Config loaded: {settings.app_name} v{settings.app_version}")
    except Exception as e:
        errors.append(f"Config import failed: {e}")

    try:
        print("Checking database...")
        from app.database import engine, Base, get_db
        print("✓ Database module loaded")
    except Exception as e:
        errors.append(f"Database import failed: {e}")

    try:
        print("Checking models...")
        from app.models import db_models, schemas
        print("✓ Models loaded")
    except Exception as e:
        errors.append(f"Models import failed: {e}")

    try:
        print("Checking services...")
        from app.services import transaction_service, budget_service, goal_service
        print("✓ Services loaded")
    except Exception as e:
        errors.append(f"Services import failed: {e}")

    try:
        print("Checking API routers...")
        from app.api.v1 import users, accounts, categories, transactions
        from app.api.v1 import recurring, budgets, goals, tags, attachments
        print("✓ All API routers loaded")
    except Exception as e:
        errors.append(f"API routers import failed: {e}")

    try:
        print("Checking main app...")
        from app.main import app
        print("✓ FastAPI app created")
    except Exception as e:
        errors.append(f"Main app import failed: {e}")

    if errors:
        print("\n❌ ERRORS FOUND:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✅ All imports successful! Project setup is correct.")
        return True

def check_file_structure():
    """Check if all required files exist"""
    print("\nChecking file structure...")

    base_path = Path(__file__).parent
    required_files = [
        "app/__init__.py",
        "app/main.py",
        "app/config.py",
        "app/database.py",
        "app/models/__init__.py",
        "app/models/db_models.py",
        "app/models/schemas.py",
        "app/api/__init__.py",
        "app/api/dependencies.py",
        "app/api/v1/__init__.py",
        "app/api/v1/users.py",
        "app/api/v1/accounts.py",
        "app/api/v1/categories.py",
        "app/api/v1/transactions.py",
        "app/api/v1/recurring.py",
        "app/api/v1/budgets.py",
        "app/api/v1/goals.py",
        "app/api/v1/tags.py",
        "app/api/v1/attachments.py",
        "app/services/__init__.py",
        "app/services/transaction_service.py",
        "app/services/budget_service.py",
        "app/services/goal_service.py",
        "requirements.txt",
        "Dockerfile",
        "docker-compose.yml",
        "alembic.ini",
        "alembic/env.py",
        "alembic/script.py.mako",
        ".env.example",
        "README.md",
        "Makefile",
    ]

    missing = []
    for file_path in required_files:
        if not (base_path / file_path).exists():
            missing.append(file_path)
            print(f"  ❌ Missing: {file_path}")
        else:
            print(f"  ✓ {file_path}")

    if missing:
        print(f"\n❌ {len(missing)} files missing!")
        return False
    else:
        print("\n✅ All required files present!")
        return True

if __name__ == "__main__":
    print("=" * 60)
    print("FinanzApp - Setup Verification")
    print("=" * 60)

    file_check = check_file_structure()
    import_check = verify_imports()

    print("\n" + "=" * 60)
    if file_check and import_check:
        print("✅ ALL CHECKS PASSED - Ready to deploy!")
        sys.exit(0)
    else:
        print("❌ SOME CHECKS FAILED - Fix errors before deploying")
        sys.exit(1)
