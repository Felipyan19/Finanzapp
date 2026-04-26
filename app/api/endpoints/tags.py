from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
from uuid import UUID

from app.api.dependencies import get_db, get_current_active_user
from app.models import db_models, schemas

router = APIRouter(prefix="/tags", tags=["tags"])


@router.post("", response_model=schemas.TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    tag: schemas.TagCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Create a new tag."""
    existing_tag = db.query(db_models.Tag).filter(
        db_models.Tag.user_id == current_user.id,
        db_models.Tag.name == tag.name,
    ).first()
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag with this name already exists for user",
        )

    tag_data = tag.model_dump()
    tag_data["user_id"] = current_user.id
    db_tag = db_models.Tag(**tag_data)
    db.add(db_tag)
    try:
        db.commit()
        db.refresh(db_tag)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag with this name already exists for user",
        )
    return db_tag


@router.get("", response_model=List[schemas.TagResponse])
def list_tags(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """List all tags for the authenticated user."""
    return (
        db.query(db_models.Tag)
        .filter(db_models.Tag.user_id == current_user.id)
        .order_by(db_models.Tag.name)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{tag_id}", response_model=schemas.TagResponse)
def get_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Get a tag by ID."""
    db_tag = db.query(db_models.Tag).filter(
        db_models.Tag.id == tag_id,
        db_models.Tag.user_id == current_user.id,
    ).first()
    if not db_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return db_tag


@router.put("/{tag_id}", response_model=schemas.TagResponse)
def update_tag(
    tag_id: UUID,
    tag_update: schemas.TagUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Update a tag."""
    db_tag = db.query(db_models.Tag).filter(
        db_models.Tag.id == tag_id,
        db_models.Tag.user_id == current_user.id,
    ).first()
    if not db_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    update_data = tag_update.model_dump(exclude_unset=True)
    if "name" in update_data:
        existing_tag = db.query(db_models.Tag).filter(
            db_models.Tag.user_id == current_user.id,
            db_models.Tag.name == update_data["name"],
            db_models.Tag.id != tag_id,
        ).first()
        if existing_tag:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tag with this name already exists for user",
            )

    for field, value in update_data.items():
        setattr(db_tag, field, value)

    try:
        db.commit()
        db.refresh(db_tag)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag with this name already exists for user",
        )
    return db_tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Delete a tag."""
    db_tag = db.query(db_models.Tag).filter(
        db_models.Tag.id == tag_id,
        db_models.Tag.user_id == current_user.id,
    ).first()
    if not db_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    db.delete(db_tag)
    db.commit()
    return None


@router.post("/transactions/{transaction_id}/tags/{tag_id}", status_code=status.HTTP_201_CREATED)
def assign_tag_to_transaction(
    transaction_id: UUID,
    tag_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Assign a tag to a transaction."""
    transaction = db.query(db_models.Transaction).filter(
        db_models.Transaction.id == transaction_id,
        db_models.Transaction.user_id == current_user.id,
    ).first()
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    tag = db.query(db_models.Tag).filter(
        db_models.Tag.id == tag_id,
        db_models.Tag.user_id == current_user.id,
    ).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    existing = db.query(db_models.TransactionTag).filter(
        db_models.TransactionTag.transaction_id == transaction_id,
        db_models.TransactionTag.tag_id == tag_id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag already assigned to transaction",
        )

    db.add(db_models.TransactionTag(transaction_id=transaction_id, tag_id=tag_id))
    db.commit()
    return {"message": "Tag assigned successfully"}


@router.delete("/transactions/{transaction_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_tag_from_transaction(
    transaction_id: UUID,
    tag_id: UUID,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Remove a tag from a transaction."""
    transaction_tag = db.query(db_models.TransactionTag).filter(
        db_models.TransactionTag.transaction_id == transaction_id,
        db_models.TransactionTag.tag_id == tag_id,
    ).first()
    if not transaction_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not assigned to transaction")

    db.delete(transaction_tag)
    db.commit()
    return None
