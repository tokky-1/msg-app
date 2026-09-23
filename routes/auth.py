from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.dependencies import get_current_user
from core.security import create_access_token
from db.connect import get_db
from models.user import User
from schema.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from services.user_service import UserService

authrouter = APIRouter(prefix="/auth", tags=["auth"])


@authrouter.post("/register", response_model=UserResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return UserService(db).register(data)


@authrouter.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = UserService(db).authenticate(data)
    return TokenResponse(access_token=create_access_token({"sub": str(user.id)}))


@authrouter.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
