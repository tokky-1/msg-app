from pydantic import BaseModel, Field, EmailStr, ConfigDict

class RegisterRequest(BaseModel): # when using model object is always a dictionary
    email: EmailStr = Field(description="User's Email")
    username: str = Field(min_length=1, max_length=150, description="User's name")
    password : str = Field(description="password of the User")

class LoginRequest(BaseModel):
    # Capped here as well as on register: a login attempt is written to
    # auth_attempts by an unauthenticated caller, so the length has to be
    # bounded before it reaches the database.
    username: str = Field(min_length=1, max_length=150, description="User's name")
    password : str = Field(description="password of the User")

class TokenResponse(BaseModel):
    access_token : str  
    token_type:  str = "bearer"

class UserResponse(BaseModel):
    """Your own account. Only ever returned to the user it describes."""
    id: int
    username: str
    email: str
    model_config = ConfigDict(from_attributes=True)


class PublicUser(BaseModel):
    """Someone else's account, as anyone logged in may see it.

    No email: looking a user up is how you start a conversation, and that only
    needs an id. Returning the address here would let any account harvest the
    email behind every username it can guess.
    """
    id: int
    username: str
    model_config = ConfigDict(from_attributes=True)