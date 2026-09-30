from pwdlib import PasswordHash
import jwt
from datetime import datetime, timedelta, timezone
from core.config import settings

password_hash = PasswordHash.recommended()  

def createhash(password:str)-> str:  
    return password_hash.hash(password)
    
def verifyhash(plainpassword:str, hashedpassword:str)-> bool:
    return password_hash.verify(plainpassword,hashedpassword)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> dict:
    # Raises jwt.ExpiredSignatureError / jwt.InvalidTokenError; the caller decides how to respond.
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])