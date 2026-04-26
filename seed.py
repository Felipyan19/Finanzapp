#!/usr/bin/env python3
"""
Seed script — crea un usuario inicial en la base de datos.

Uso local:
    python seed.py

Uso con Docker:
    docker-compose exec api python seed.py
    docker-compose exec api python seed.py --email otro@correo.com --password otraclave --name "Otro Usuario"

Variables de entorno opcionales:
    SEED_EMAIL    (default: admin@finanzapp.com)
    SEED_PASSWORD (default: Admin1234!)
    SEED_NAME     (default: Administrador)
    SEED_CURRENCY (default: COP)
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, engine
from app.models import db_models
from app.models.db_models import Base
from app.services.auth_service import hash_password


def seed(email: str, password: str, name: str, currency: str) -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.query(db_models.User).filter(db_models.User.email == email).first()
        if existing:
            print(f"[seed] El usuario '{email}' ya existe — no se creó uno nuevo.")
            print(f"       ID: {existing.id}")
            return

        user = db_models.User(
            email=email,
            name=name,
            currency=currency,
            timezone="America/Bogota",
            hashed_password=hash_password(password),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        print("=" * 50)
        print("[seed] Usuario creado exitosamente")
        print(f"  ID       : {user.id}")
        print(f"  Nombre   : {user.name}")
        print(f"  Email    : {user.email}")
        print(f"  Moneda   : {user.currency}")
        print(f"  Password : {password}")
        print("=" * 50)

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crea un usuario inicial en la base de datos.")
    parser.add_argument("--email",    default=os.getenv("SEED_EMAIL",    "admin@finanzapp.com"))
    parser.add_argument("--password", default=os.getenv("SEED_PASSWORD", "Admin1234!"))
    parser.add_argument("--name",     default=os.getenv("SEED_NAME",     "Administrador"))
    parser.add_argument("--currency", default=os.getenv("SEED_CURRENCY", "COP"))
    args = parser.parse_args()

    seed(
        email=args.email,
        password=args.password,
        name=args.name,
        currency=args.currency,
    )
