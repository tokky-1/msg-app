from pydantic import BaseModel, Field, EmailStr, ConfigDict

class RegisterRequest(BaseModel): # when using model object is always a dictionary
    email: EmailStr = Field(description="User's Email")
    username :str = Field(description="User's name") 
    password : str = Field(description="password of the User")

class LoginRequest(BaseModel):
    username:  str = Field(description=" User's name")
    password : str = Field(description="password of the User")

class TokenResponse(BaseModel):
    access_token : str  
    token_type:  str = "bearer"

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    model_config = ConfigDict(from_attributes=True)