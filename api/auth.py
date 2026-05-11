from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt as _bcrypt
from jose import JWTError, jwt

from src.security import Role, UserContext

SECRET_KEY = os.getenv("JWT_SECRET", "change-me-in-production")
ALGORITHM = "HS256"
TOKEN_TTL_HOURS = 24

USERS_FILE = Path(__file__).parent / "users.json"


def _hash(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def _verify(password: str, hashed: str) -> bool:
    return _bcrypt.checkpw(password.encode(), hashed.encode())


def _load() -> dict:
    if not USERS_FILE.exists():
        return {}
    return json.loads(USERS_FILE.read_text())


def _save(users: dict) -> None:
    USERS_FILE.write_text(json.dumps(users, indent=2))


def ensure_default_admin() -> None:
    users = _load()
    if "admin" not in users:
        password = os.getenv("ADMIN_PASSWORD", "admin123")
        users["admin"] = {
            "hashed_password": _hash(password),
            "role": "admin",
            "allowed_classes": [],
        }
        _save(users)
        print("Created default admin user (set ADMIN_PASSWORD in .env to change)")


def authenticate_user(username: str, password: str) -> Optional[UserContext]:
    users = _load()
    data = users.get(username)
    if not data or not _verify(password, data["hashed_password"]):
        return None
    try:
        role = Role(data["role"])
    except ValueError:
        return None
    return UserContext(
        user_id=username,
        role=role,
        allowed_classes=data.get("allowed_classes", []),
    )


def create_access_token(user: UserContext) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    return jwt.encode(
        {"sub": user.user_id, "role": user.role.value,
         "allowed_classes": user.allowed_classes, "exp": expire},
        SECRET_KEY, algorithm=ALGORITHM,
    )


def decode_token(token: str) -> Optional[UserContext]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role_str = payload.get("role")
        if not username or not role_str:
            return None
        return UserContext(
            user_id=username,
            role=Role(role_str),
            allowed_classes=payload.get("allowed_classes", []),
        )
    except (JWTError, ValueError):
        return None



def list_users() -> list[dict]:
    return [
        {"username": k, "role": v["role"], "allowed_classes": v.get("allowed_classes", [])}
        for k, v in _load().items()
    ]


def create_user(username: str, password: str, role: str, allowed_classes: list[str]) -> bool:
    users = _load()
    if username in users:
        return False
    users[username] = {
        "hashed_password": _hash(password),
        "role": role,
        "allowed_classes": allowed_classes,
    }
    _save(users)
    return True


def delete_user(username: str) -> bool:
    users = _load()
    if username not in users or username == "admin":
        return False
    del users[username]
    _save(users)
    return True
