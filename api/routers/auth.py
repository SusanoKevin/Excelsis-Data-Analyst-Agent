from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import (
    authenticate_user, create_access_token,
    create_user, delete_user, list_users,
)
from api.deps import get_current_user
from api.models import CreateUserRequest, LoginRequest, Token, UserInfo
from src.security import Role, UserContext

router = APIRouter()


@router.post("/login", response_model=Token)
def login(body: LoginRequest):
    user = authenticate_user(body.username, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect username or password")
    return Token(
        access_token=create_access_token(user),
        role=user.role.value,
        user_id=user.user_id,
        allowed_classes=user.allowed_classes,
    )


@router.get("/me", response_model=UserInfo)
def me(user: UserContext = Depends(get_current_user)):
    return UserInfo(user_id=user.user_id, role=user.role.value,
                    allowed_classes=user.allowed_classes)


@router.get("/users")
def get_users(user: UserContext = Depends(get_current_user)):
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    return list_users()


@router.post("/users", status_code=201)
def add_user(body: CreateUserRequest, user: UserContext = Depends(get_current_user)):
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    if body.role not in [r.value for r in Role]:
        raise HTTPException(status_code=400, detail=f"Invalid role '{body.role}'")
    ok = create_user(body.username, body.password, body.role, body.allowed_classes)
    if not ok:
        raise HTTPException(status_code=409, detail="Username already exists")
    return {"message": f"User '{body.username}' created"}


@router.delete("/users/{username}")
def remove_user(username: str, user: UserContext = Depends(get_current_user)):
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    ok = delete_user(username)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found or cannot delete admin")
    return {"message": f"User '{username}' deleted"}
