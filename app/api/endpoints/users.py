from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.api.dependencies import get_db, get_current_active_user
from app.models import db_models, schemas

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=schemas.UserResponse)
def get_my_profile(
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get the authenticated user's profile (alias for /auth/me)."""
    return current_user


@router.get("/{user_id}", response_model=schemas.UserResponse)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get a user by ID (only own profile allowed)."""
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to other users' profiles is not allowed",
        )
    return current_user


@router.put("/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: UUID,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Update a user's profile (only own profile allowed)."""
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update other users' profiles",
        )

    for field, value in user_update.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Deactivate own account."""
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate other users",
        )

    current_user.is_active = False
    db.commit()
    return None
