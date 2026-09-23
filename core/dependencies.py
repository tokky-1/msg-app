import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from core.errors import AuthenticationError
from core.security import decode_access_token
from db.connect import get_db
from models.user import User
from repository.user_repo import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
        # Bad signature, expired, malformed, missing or non-numeric sub: all the same to the client.
        raise AuthenticationError()

    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        # Valid token for a user that has since been deleted.
        raise AuthenticationError()

    return user
