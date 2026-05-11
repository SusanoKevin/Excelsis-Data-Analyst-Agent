"""
RBAC + data-level security for Excelsis 360.

Two-layer enforcement:
  1. Tool level  – SecurityManager.require() raises AccessDeniedError before any work runs
  2. Data level  – SecurityManager.filter_df() strips rows outside user.allowed_classes

Role → permission mapping:
  ADMIN     – all permissions, all classes
  TEACHER   – read own classes, generate dashboards
  COUNSELOR – read own classes, at-risk list, generate dashboards
  VIEWER    – read own classes only
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    READ_OWN_CLASSES   = "read_own_classes"
    READ_AT_RISK       = "read_at_risk"
    GENERATE_DASHBOARD = "generate_dashboard"
    INGEST_DATA        = "ingest_data"
    VIEW_AUDIT_LOG     = "view_audit_log"


class Role(str, Enum):
    ADMIN     = "admin"
    TEACHER   = "teacher"
    COUNSELOR = "counselor"
    VIEWER    = "viewer"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: set(Permission),
    Role.TEACHER: {
        Permission.READ_OWN_CLASSES,
        Permission.GENERATE_DASHBOARD,
        Permission.INGEST_DATA,
    },
    Role.COUNSELOR: {
        Permission.READ_OWN_CLASSES,
        Permission.READ_AT_RISK,
        Permission.GENERATE_DASHBOARD,
    },
    Role.VIEWER: {
        Permission.READ_OWN_CLASSES,
    },
}


@dataclass
class UserContext:
    user_id: str
    role: Role
    # Empty list = no class restriction (admin only)
    allowed_classes: list[str] = field(default_factory=list)

    @property
    def permissions(self) -> set[Permission]:
        return ROLE_PERMISSIONS.get(self.role, set())

    def can(self, permission: Permission) -> bool:
        return permission in self.permissions


class AccessDeniedError(PermissionError):
    pass


class SecurityManager:
    def __init__(self) -> None:
        self._audit: list[dict] = []

    def require(self, user: UserContext, permission: Permission, resource: str = "") -> None:
        granted = user.can(permission)
        self._record(user, permission, resource, granted)
        if not granted:
            raise AccessDeniedError(
                f"User '{user.user_id}' (role={user.role.value}) "
                f"lacks '{permission.value}' on '{resource or 'N/A'}'"
            )

    def filter_df(self, df: pd.DataFrame, user: UserContext) -> pd.DataFrame:
        if df.empty or user.role == Role.ADMIN:
            return df
        if "class" in df.columns and user.allowed_classes:
            return df[df["class"].isin(user.allowed_classes)].copy()
        return df

    def _record(self, user: UserContext, perm: Permission, resource: str, granted: bool) -> None:
        self._audit.append({
            "ts": time.time(), "user": user.user_id, "role": user.role.value,
            "perm": perm.value, "resource": resource, "granted": granted,
        })
        logger.log(
            logging.INFO if granted else logging.WARNING,
            "ACCESS %s | user=%s role=%s perm=%s resource=%s",
            "GRANTED" if granted else "DENIED",
            user.user_id, user.role.value, perm.value, resource or "-",
        )

    def audit_log(self) -> list[dict]:
        return list(self._audit)


def _parse_token_env() -> dict[str, UserContext]:
    registry: dict[str, UserContext] = {}
    for entry in os.getenv("EXCELSIS_TOKENS", "").split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(":", 2)
        if len(parts) < 2:
            continue
        token, role_str = parts[0], parts[1]
        classes_str = parts[2] if len(parts) == 3 else ""
        try:
            role = Role(role_str.lower())
        except ValueError:
            logger.warning("Unknown role '%s' in EXCELSIS_TOKENS, skipping", role_str)
            continue
        allowed = [c.strip() for c in classes_str.split("|") if c.strip()]
        registry[token] = UserContext(user_id=f"token_{token[:6]}", role=role, allowed_classes=allowed)
    return registry


TOKEN_REGISTRY: dict[str, UserContext] = _parse_token_env()
ADMIN_USER = UserContext(user_id="admin", role=Role.ADMIN)
security = SecurityManager()
