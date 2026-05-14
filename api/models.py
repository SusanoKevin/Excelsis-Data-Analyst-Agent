from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user_id:      str


class UserInfo(BaseModel):
    user_id: str


class CreateUserRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    message: str
