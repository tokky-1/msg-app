from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from core.dependencies import get_current_user
from core.security import create_access_token
from db.connect import get_db
from models.user import User
from schema.auth import LoginRequest, PublicUser, RegisterRequest, TokenResponse, UserResponse
from services.user_service import UserService

authrouter = APIRouter(prefix="/auth", tags=["auth"])


@authrouter.post("/register", response_model=UserResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return UserService(db).register(data)


@authrouter.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = UserService(db).authenticate(data)
    return TokenResponse(access_token=create_access_token({"sub": str(user.id)}))


@authrouter.post("/token", response_model=TokenResponse)
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 password flow, form-encoded. Backs the Swagger Authorize button.

    /auth/login is the same exchange for JSON clients; this one exists because the
    flow requires form encoding.
    """
    user = UserService(db).authenticate(LoginRequest(username=form.username, password=form.password))
    return TokenResponse(access_token=create_access_token({"sub": str(user.id)}))


@authrouter.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@authrouter.get("/users/{username}", response_model=PublicUser)
def get_user(
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resolve a username to the account behind it.

    Sending needs a receiver_id, and a client that has never messaged someone
    has no way to learn theirs: /messages/conversation/{username} returns an
    empty list for a fresh conversation, which carries no id. Reuses the
    conversation-partner lookup, so an unknown username 404s and your own
    username is refused exactly as it is everywhere else.

    Responds with PublicUser, not UserResponse: the caller needs the id, not
    the other person's email address.
    """
    return UserService(db).get_conversation_partner(current_user.id, username)
