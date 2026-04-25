from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.api.dependencies import get_db
from app.models import db_models, schemas

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("", response_model=schemas.CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    """Create a new category"""
    # Verify user exists
    user = db.query(db_models.User).filter(db_models.User.id == category.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify parent category exists if provided
    if category.parent_id:
        parent = db.query(db_models.Category).filter(db_models.Category.id == category.parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent category not found"
            )
        # Ensure parent belongs to same user
        if parent.user_id != category.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent category must belong to the same user"
            )

    db_category = db_models.Category(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@router.get("/{category_id}", response_model=schemas.CategoryResponse)
def get_category(category_id: UUID, db: Session = Depends(get_db)):
    """Get a category by ID"""
    db_category = db.query(db_models.Category).filter(db_models.Category.id == category_id).first()
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return db_category


@router.get("", response_model=List[schemas.CategoryResponse])
def list_categories(
    user_id: UUID = None,
    category_type: str = None,
    parent_id: UUID = None,
    is_active: bool = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List categories with optional filters"""
    query = db.query(db_models.Category)

    if user_id:
        query = query.filter(db_models.Category.user_id == user_id)

    if category_type:
        query = query.filter(db_models.Category.category_type == category_type)

    if parent_id:
        query = query.filter(db_models.Category.parent_id == parent_id)

    if is_active is not None:
        query = query.filter(db_models.Category.is_active == is_active)

    categories = query.offset(skip).limit(limit).all()
    return categories


@router.put("/{category_id}", response_model=schemas.CategoryResponse)
def update_category(
    category_id: UUID,
    category_update: schemas.CategoryUpdate,
    db: Session = Depends(get_db)
):
    """Update a category"""
    db_category = db.query(db_models.Category).filter(db_models.Category.id == category_id).first()
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    update_data = category_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_category, field, value)

    db.commit()
    db.refresh(db_category)
    return db_category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: UUID, db: Session = Depends(get_db)):
    """Deactivate a category (soft delete)"""
    db_category = db.query(db_models.Category).filter(db_models.Category.id == category_id).first()
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    db_category.is_active = False
    db.commit()
    return None
