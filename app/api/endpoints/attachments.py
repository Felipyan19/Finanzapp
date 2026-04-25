from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from uuid import UUID, uuid4
from pathlib import Path

from app.api.dependencies import get_db
from app.models import db_models, schemas
from app.config import settings

router = APIRouter(prefix="/attachments", tags=["attachments"])

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx', '.xls', '.xlsx', '.txt'}
MAX_FILE_SIZE = settings.max_file_size * 1024 * 1024  # Convert MB to bytes


def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type {file_ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}")


def save_upload_file(upload_file: UploadFile, destination: Path) -> None:
    """Save uploaded file to destination"""
    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    finally:
        upload_file.file.close()


@router.post("/transactions/{transaction_id}", response_model=schemas.AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    transaction_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload an attachment for a transaction"""
    # Verify transaction exists
    transaction = db.query(db_models.Transaction).filter(
        db_models.Transaction.id == transaction_id
    ).first()
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    # Validate file
    try:
        validate_file(file)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Create upload directory if it doesn't exist
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid4()}{file_ext}"
    file_path = upload_dir / unique_filename

    # Save file
    save_upload_file(file, file_path)

    # Get file size
    file_size = os.path.getsize(file_path)

    # Check file size
    if file_size > MAX_FILE_SIZE:
        os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.max_file_size}MB"
        )

    # Create attachment record
    db_attachment = db_models.TransactionAttachment(
        transaction_id=transaction_id,
        file_name=file.filename,
        file_url="",
        file_path=str(file_path),
        mime_type=file.content_type,
        file_size=file_size
    )
    db.add(db_attachment)
    db.commit()
    db.refresh(db_attachment)

    # Store canonical download URL once ID is available.
    db_attachment.file_url = f"/api/v1/attachments/{db_attachment.id}"
    db.commit()
    db.refresh(db_attachment)

    return db_attachment


@router.get("/transactions/{transaction_id}", response_model=List[schemas.AttachmentResponse])
def list_transaction_attachments(
    transaction_id: UUID,
    db: Session = Depends(get_db)
):
    """List all attachments for a transaction"""
    # Verify transaction exists
    transaction = db.query(db_models.Transaction).filter(
        db_models.Transaction.id == transaction_id
    ).first()
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    attachments = db.query(db_models.TransactionAttachment).filter(
        db_models.TransactionAttachment.transaction_id == transaction_id
    ).all()

    return attachments


@router.get("/{attachment_id}")
def download_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db)
):
    """Download an attachment file"""
    attachment = db.query(db_models.TransactionAttachment).filter(
        db_models.TransactionAttachment.id == attachment_id
    ).first()
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found"
        )

    file_path = Path(attachment.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )

    return FileResponse(
        path=file_path,
        filename=attachment.file_name,
        media_type=attachment.mime_type or 'application/octet-stream'
    )


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete an attachment"""
    attachment = db.query(db_models.TransactionAttachment).filter(
        db_models.TransactionAttachment.id == attachment_id
    ).first()
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found"
        )

    # Delete file from disk
    file_path = Path(attachment.file_path)
    if file_path.exists():
        os.remove(file_path)

    # Delete database record
    db.delete(attachment)
    db.commit()

    return None
