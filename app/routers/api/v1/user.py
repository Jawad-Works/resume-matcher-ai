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
import json
from passlib.context import CryptContext

SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

USERS_FILE = "users.json"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def get_user_by_email_json(email):
    users = load_users()
    for user in users:
        if user["email"] == email:
            return user
    return None


def create_user_json(email, password):
    users = load_users()
    if any(u["email"] == email for u in users):
        return None
    new_id = max([u["id"] for u in users], default=0) + 1
    hashed_password = pwd_context.hash(password)
    user = {
        "id": new_id,
        "email": email,
        "hashed_password": hashed_password,
        "is_active": True,
    }
    users.append(user)
    save_users(users)
    return user


def update_user_password_json(email, new_password):
    users = load_users()
    for user in users:
        if user["email"] == email:
            user["hashed_password"] = pwd_context.hash(new_password)
            save_users(users)
            return True
    return False


def authenticate_user_json(email, password):
    user = get_user_by_email_json(email)
    if not user:
        return None
    if not pwd_context.verify(password, user["hashed_password"]):
        return None
    return user


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
def signup(user: UserCreate):
    """Signup a new user using JSON file storage."""
    # db_user = crud.get_user_by_email(db, user.email)
    # if db_user:
    #     return {"success": False, "error": "Email already registered"}
    # created_user = crud.create_user(db, user)
    created_user = create_user_json(user.email, user.password)
    if not created_user:
        return {"success": False, "error": "Email already registered"}
    access_token = create_access_token(data={"sub": created_user["email"]})
    return {
        "success": True,
        "data": {
            "token": access_token,
            "user": {
                "id": created_user["id"],
                "email": created_user["email"],
                "is_active": created_user["is_active"],
            },
        },
    }


@router.post("/login")
def login(data: LoginRequest):
    """Login user using JSON file storage."""
    # user = crud.authenticate_user(db, data.email, data.password)
    user = authenticate_user_json(data.email, data.password)
    if not user:
        return {"success": False, "error": "Incorrect email or password"}
    access_token = create_access_token(data={"sub": user["email"]})
    return {
        "success": True,
        "data": {
            "token": access_token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "is_active": user["is_active"],
            },
        },
    }


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest):
    """Forgot password using JSON file storage."""
    # user = crud.get_user_by_email(db, data.email)
    # if not user:
    #     return {"success": False, "error": "User not found"}
    updated = update_user_password_json(data.email, data.newPassword)
    if not updated:
        return {"success": False, "error": "User not found"}
    return {"success": True, "data": {"message": "Password updated successfully."}}
