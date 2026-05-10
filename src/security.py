"""
RBAC + data-level security for Excelsis 360.

Roles
-----
ADMIN      – unrestricted; all permissions; all classes
TEACHER    – read own classes; generate dashboards
COUNSELOR  – read own classes; see at-risk; web search; generate dashboards
VIEWER     – read own classes only

Permissions are enforced at two levels:
  1. Tool level   – SecurityManager.require() raises AccessDeniedError before any work
  2. Data level   – SecurityManager.filter_df() strips rows the user cannot see
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & constants
# ---------------------------------------------------------------------------

class Permission(str, Enum):
    READ_OWN_CLASSES  = "read_own_classes"
    READ_ALL_CLASSES  = "read_all_classes"
    READ_AT_RISK      = "read_at_risk"
    GENERATE_DASHBOARD = "generate_dashboard"
    INGEST_DATA       = "ingest_data"
    VIEW_AUDIT_LOG    = "view_audit_log"


class Role(str, Enum):
    ADMIN     = "admin"
    TEACHER   = "teacher"
    COUNSELOR = "counselor"
    VIEWER    = "viewer"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: set(Permission),  # all permissions
    Role.TEACHER: {
        Permission.READ_OWN_CLASSES,
        Permission.GENERATE_DASHBOARD,
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


# ---------------------------------------------------------------------------
# User context
# ---------------------------------------------------------------------------

@dataclass
class UserContext:
    user_id: str
    role: Role
    # Empty list means no class restriction (only meaningful for ADMIN)
    allowed_classes: list[str] = field(default_factory=list)

    @property
    def permissions(self) -> set[Permission]:
        return ROLE_PERMISSIONS.get(self.role, set())

    def can(self, permission: Permission) -> bool:
        return permission in self.permissions

    def can_access_class(self, class_name: str) -> bool:
        if self.role == Role.ADMIN or not self.allowed_classes:
            return True
        return class_name in self.allowed_classes

    def visible_classes(self, all_classes: list[str]) -> list[str]:
        if self.role == Role.ADMIN or not self.allowed_classes:
            return all_classes
        return [c for c in all_classes if c in self.allowed_classes]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AccessDeniedError(PermissionError):
    pass


# ---------------------------------------------------------------------------
# Security manager
# ---------------------------------------------------------------------------

class SecurityManager:
    def __init__(self) -> None:
        self._audit: list[dict] = []

    # -- permission check ----------------------------------------------------

    def require(self, user: UserContext, permission: Permission, resource: str = "") -> None:
        """Raise AccessDeniedError if user lacks permission; always audits."""
        granted = user.can(permission)
        self._record(user, permission, resource, granted)
        if not granted:
            raise AccessDeniedError(
                f"User '{user.user_id}' (role={user.role.value}) "
                f"lacks '{permission.value}' on '{resource or 'N/A'}'"
            )

    # -- data-level filtering ------------------------------------------------

    def filter_df(self, df: pd.DataFrame, user: UserContext) -> pd.DataFrame:
        """Return a copy of df containing only rows the user may see."""
        if df.empty or user.role == Role.ADMIN:
            return df
        if "class" in df.columns and user.allowed_classes:
            mask = df["class"].isin(user.allowed_classes)
            return df[mask].copy()
        return df

    # -- audit ---------------------------------------------------------------

    def _record(self, user: UserContext, perm: Permission, resource: str, granted: bool) -> None:
        entry = {
            "ts":       time.time(),
            "user":     user.user_id,
            "role":     user.role.value,
            "perm":     perm.value,
            "resource": resource,
            "granted":  granted,
        }
        self._audit.append(entry)
        lvl = logging.INFO if granted else logging.WARNING
        logger.log(
            lvl,
            "ACCESS %s | user=%s role=%s perm=%s resource=%s",
            "GRANTED" if granted else "DENIED",
            user.user_id, user.role.value, perm.value, resource or "-",
        )

    def audit_log(self) -> list[dict]:
        return list(self._audit)


# ---------------------------------------------------------------------------
# Token registry (for MCP server)
# Maps API token → UserContext
# Populate via environment: EXCELSIS_TOKENS="token1:admin:,token2:teacher:10A|10B"
# ---------------------------------------------------------------------------

import os

def _parse_token_env() -> dict[str, UserContext]:
    raw = os.getenv("EXCELSIS_TOKENS", "")
    registry: dict[str, UserContext] = {}
    for entry in raw.split(","):
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
