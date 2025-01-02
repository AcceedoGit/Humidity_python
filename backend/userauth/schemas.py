from pydantic import BaseModel,EmailStr

class LoginRequest(BaseModel):
    username: str
    password: str

from pydantic import BaseModel, Field

class User(BaseModel):
    user_ID: str = Field(...,)
    username: str = Field(...,)
    role: str = Field(...,)
    emailId: str = Field(...,)
    phoneNo: str = Field(...,)
    password: str = Field(...,)


