"""User-related API routes and authentication logic."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud
from app.database.database import SessionLocal
from jose import jwt
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer
from app.schemas.user import UserCreate, LoginRequest, ForgotPasswordRequest
import os

SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login")

router = APIRouter(prefix="/user", tags=["user"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    """_summary_

    Args:
        user (UserCreate): _description_
        db (Session, optional): _description_. Defaults to Depends(get_db).

    Returns:
        _type_: _description_
    """
    try:
        db_user = crud.get_user_by_email(db, user.email)
        if db_user:
            return {"success": False, "error": "Email already registered"}

        created_user = crud.create_user(db, user)
        access_token = create_access_token(data={"sub": created_user.email})

        return {
            "success": True,
            "data": {
                "token": access_token,
                "user": {
                    "id": created_user.id,
                    "email": created_user.email,
                    "is_active": created_user.is_active,
                },
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = crud.authenticate_user(db, data.email, data.password)
        if not user:
            return {"success": False, "error": "Incorrect email or password"}
        access_token = create_access_token(data={"sub": user.email})
        return {
            "success": True,
            "data": {
                "token": access_token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "is_active": user.is_active,
                },
            },
        }
    except HTTPException as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    try:
        user = crud.get_user_by_email(db, data.email)
        if not user:
            return {"success": False, "error": "User not found"}
        # Hash the new password and update
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = pwd_context.hash(data.newPassword)
        setattr(user, "hashed_password", hashed)
        db.commit()
        return {"success": True, "data": {"message": "Password updated successfully."}}
    except Exception as e:
        return {"success": False, "error": str(e)}
