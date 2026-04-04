from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
from uuid import UUID

from app.api.dependencies import get_db
from app.models import db_models, schemas

router = APIRouter(prefix="/tags", tags=["tags"])


@router.post("", response_model=schemas.TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(tag: schemas.TagCreate, db: Session = Depends(get_db)):
    """Create a new tag"""
    # Verify user exists
    user = db.query(db_models.User).filter(db_models.User.id == tag.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if tag with same name already exists for user
    existing_tag = db.query(db_models.Tag).filter(
        db_models.Tag.user_id == tag.user_id,
        db_models.Tag.name == tag.name
    ).first()
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag with this name already exists for user"
        )

    db_tag = db_models.Tag(**tag.model_dump())
    db.add(db_tag)
    try:
        db.commit()
        db.refresh(db_tag)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag with this name already exists for user"
        )

    return db_tag


@router.get("/{tag_id}", response_model=schemas.TagResponse)
def get_tag(tag_id: UUID, db: Session = Depends(get_db)):
    """Get a tag by ID"""
    db_tag = db.query(db_models.Tag).filter(db_models.Tag.id == tag_id).first()
    if not db_tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    return db_tag


@router.get("", response_model=List[schemas.TagResponse])
def list_tags(
    user_id: UUID = Query(...),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all tags for a user"""
    tags = db.query(db_models.Tag).filter(
        db_models.Tag.user_id == user_id
    ).order_by(db_models.Tag.name).offset(skip).limit(limit).all()
    return tags


@router.put("/{tag_id}", response_model=schemas.TagResponse)
def update_tag(
    tag_id: UUID,
    tag_update: schemas.TagUpdate,
    db: Session = Depends(get_db)
):
    """Update a tag"""
    db_tag = db.query(db_models.Tag).filter(db_models.Tag.id == tag_id).first()
    if not db_tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    update_data = tag_update.model_dump(exclude_unset=True)

    # Check for name conflicts if name is being updated
    if 'name' in update_data:
        existing_tag = db.query(db_models.Tag).filter(
            db_models.Tag.user_id == db_tag.user_id,
            db_models.Tag.name == update_data['name'],
            db_models.Tag.id != tag_id
        ).first()
        if existing_tag:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tag with this name already exists for user"
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
            detail="Tag with this name already exists for user"
        )

    return db_tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: UUID, db: Session = Depends(get_db)):
    """Delete a tag"""
    db_tag = db.query(db_models.Tag).filter(db_models.Tag.id == tag_id).first()
    if not db_tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    db.delete(db_tag)
    db.commit()
    return None


@router.post("/transactions/{transaction_id}/tags/{tag_id}", status_code=status.HTTP_201_CREATED)
def assign_tag_to_transaction(
    transaction_id: UUID,
    tag_id: UUID,
    db: Session = Depends(get_db)
):
    """Assign a tag to a transaction"""
    # Verify transaction exists
    transaction = db.query(db_models.Transaction).filter(
        db_models.Transaction.id == transaction_id
    ).first()
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    # Verify tag exists
    tag = db.query(db_models.Tag).filter(db_models.Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    # Verify tag belongs to same user as transaction
    if tag.user_id != transaction.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag does not belong to transaction user"
        )

    # Check if tag already assigned
    existing = db.query(db_models.TransactionTag).filter(
        db_models.TransactionTag.transaction_id == transaction_id,
        db_models.TransactionTag.tag_id == tag_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag already assigned to transaction"
        )

    # Create association
    transaction_tag = db_models.TransactionTag(
        transaction_id=transaction_id,
        tag_id=tag_id
    )
    db.add(transaction_tag)
    db.commit()

    return {"message": "Tag assigned successfully"}


@router.delete("/transactions/{transaction_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_tag_from_transaction(
    transaction_id: UUID,
    tag_id: UUID,
    db: Session = Depends(get_db)
):
    """Remove a tag from a transaction"""
    transaction_tag = db.query(db_models.TransactionTag).filter(
        db_models.TransactionTag.transaction_id == transaction_id,
        db_models.TransactionTag.tag_id == tag_id
    ).first()

    if not transaction_tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not assigned to transaction"
        )

    db.delete(transaction_tag)
    db.commit()
    return None
