from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.connect import get_db
from schema.auth import RegisterRequest, UserResponse
from services.user_service import UserService

authrouter = APIRouter(prefix="/auth", tags=["auth"])


@authrouter.post("/register", response_model=UserResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return UserService(db).register(data)