from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    allowed_classes: list[str]


class UserInfo(BaseModel):
    user_id: str
    role: str
    allowed_classes: list[str]


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str
    allowed_classes: list[str] = []


class ChatRequest(BaseModel):
    message: str


class UploadResponse(BaseModel):
    dataset_id: str
    rows: int
    columns: list[str]
    message: str


class DashboardResponse(BaseModel):
    url: str
