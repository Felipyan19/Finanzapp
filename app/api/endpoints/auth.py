from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_active_user
from app.models import db_models, schemas
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    """Register a new user and return tokens."""
    existing = db.query(db_models.User).filter(db_models.User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_pw = auth_service.hash_password(user_data.password)
    new_user = db_models.User(
        email=user_data.email,
        name=user_data.name,
        currency=user_data.currency,
        timezone=user_data.timezone,
        hashed_password=hashed_pw,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token_data = {"sub": str(new_user.id)}
    return schemas.TokenResponse(
        access_token=auth_service.create_access_token(token_data),
        refresh_token=auth_service.create_refresh_token(token_data),
        user=schemas.UserResponse.model_validate(new_user),
    )


@router.post("/login", response_model=schemas.TokenResponse)
def login(credentials: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password, returns JWT tokens."""
    user = auth_service.authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )

    token_data = {"sub": str(user.id)}
    return schemas.TokenResponse(
        access_token=auth_service.create_access_token(token_data),
        refresh_token=auth_service.create_refresh_token(token_data),
        user=schemas.UserResponse.model_validate(user),
    )


@router.post("/login/form", response_model=schemas.TokenResponse, include_in_schema=False)
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """OAuth2 compatible form login (used by Swagger UI)."""
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = {"sub": str(user.id)}
    return schemas.TokenResponse(
        access_token=auth_service.create_access_token(token_data),
        refresh_token=auth_service.create_refresh_token(token_data),
        user=schemas.UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_token(body: schemas.RefreshRequest, db: Session = Depends(get_db)):
    """Get a new access token using a valid refresh token."""
    payload = auth_service.decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")
    user = db.query(db_models.User).filter(db_models.User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    token_data = {"sub": str(user.id)}
    return schemas.TokenResponse(
        access_token=auth_service.create_access_token(token_data),
        refresh_token=auth_service.create_refresh_token(token_data),
        user=schemas.UserResponse.model_validate(user),
    )


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: db_models.User = Depends(get_current_active_user)):
    """Return the currently authenticated user."""
    return current_user


@router.put("/me", response_model=schemas.UserResponse)
def update_me(
    update_data: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Update the currently authenticated user's profile."""
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """Change the current user's password."""
    if not current_user.hashed_password or not auth_service.verify_password(
        body.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = auth_service.hash_password(body.new_password)
    db.commit()
    return None
