from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.api.dependencies import get_db, get_current_active_user
from app.models import db_models, schemas

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("", response_model=schemas.CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Create a new category for the authenticated user."""
    if category.parent_id:
        parent = db.query(db_models.Category).filter(
            db_models.Category.id == category.parent_id,
            db_models.Category.user_id == current_user.id,
        ).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent category not found",
            )

    category_data = category.model_dump()
    category_data["user_id"] = current_user.id

    db_category = db_models.Category(**category_data)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@router.get("", response_model=List[schemas.CategoryResponse])
def list_categories(
    category_type: str = None,
    parent_id: UUID = None,
    is_active: bool = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """List categories for the authenticated user."""
    query = db.query(db_models.Category).filter(
        db_models.Category.user_id == current_user.id
    )

    if category_type:
        query = query.filter(db_models.Category.category_type == category_type)

    if parent_id:
        query = query.filter(db_models.Category.parent_id == parent_id)

    if is_active is not None:
        query = query.filter(db_models.Category.is_active == is_active)

    return query.offset(skip).limit(limit).all()


@router.get("/{category_id}", response_model=schemas.CategoryResponse)
def get_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get a category by ID."""
    db_category = db.query(db_models.Category).filter(
        db_models.Category.id == category_id,
        db_models.Category.user_id == current_user.id,
    ).first()
    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return db_category


@router.put("/{category_id}", response_model=schemas.CategoryResponse)
def update_category(
    category_id: UUID,
    category_update: schemas.CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Update a category."""
    db_category = db.query(db_models.Category).filter(
        db_models.Category.id == category_id,
        db_models.Category.user_id == current_user.id,
    ).first()
    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    for field, value in category_update.model_dump(exclude_unset=True).items():
        setattr(db_category, field, value)

    db.commit()
    db.refresh(db_category)
    return db_category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Deactivate a category (soft delete)."""
    db_category = db.query(db_models.Category).filter(
        db_models.Category.id == category_id,
        db_models.Category.user_id == current_user.id,
    ).first()
    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    db_category.is_active = False
    db.commit()
    return None
