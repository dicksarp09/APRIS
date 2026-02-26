from enum import Enum
from typing import Set, Dict, Any, Optional
from app.security.database import get_database


class Role(str, Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


PERMISSIONS_MATRIX: Dict[Role, Set[str]] = {
    Role.VIEWER: {
        "read_public_repo",
    },
    Role.OPERATOR: {
        "read_public_repo",
        "generate_docs",
        "comment_on_repo",
    },
    Role.ADMIN: {
        "read_public_repo",
        "generate_docs",
        "comment_on_repo",
        "change_thresholds",
        "trigger_network",
    },
}


class Permission:
    READ_PUBLIC_REPO = "read_public_repo"
    GENERATE_DOCS = "generate_docs"
    COMMENT_ON_REPO = "comment_on_repo"
    CHANGE_THRESHOLDS = "change_thresholds"
    TRIGGER_NETWORK = "trigger_network"


def check_permission(role: str, permission: str) -> bool:
    try:
        user_role = Role(role)
    except ValueError:
        return False
    return permission in PERMISSIONS_MATRIX.get(user_role, set())


def get_role_permissions(role: str) -> Set[str]:
    try:
        user_role = Role(role)
    except ValueError:
        return set()
    return PERMISSIONS_MATRIX.get(user_role, set())


class RBACEnforcer:
    def __init__(self):
        self._db = None

    def _get_db(self):
        if self._db is None:
            self._db = get_database()
        return self._db

    def validate_user_role(self, user_id: str, required_role: str) -> bool:
        db = self._get_db()
        user_role = db.get_user_role(user_id)
        if not user_role:
            return False
        return user_role == required_role or self.is_admin(user_id)

    def is_admin(self, user_id: str) -> bool:
        return self.validate_user_role(user_id, Role.ADMIN)

    def can_generate_docs(self, user_id: str) -> bool:
        db = self._get_db()
        role = db.get_user_role(user_id)
        return check_permission(role, Permission.GENERATE_DOCS) if role else False

    def can_comment_on_repo(self, user_id: str) -> bool:
        db = self._get_db()
        role = db.get_user_role(user_id)
        return check_permission(role, Permission.COMMENT_ON_REPO) if role else False

    def can_change_thresholds(self, user_id: str) -> bool:
        db = self._get_db()
        role = db.get_user_role(user_id)
        return check_permission(role, Permission.CHANGE_THRESHOLDS) if role else False

    def can_trigger_network(self, user_id: str) -> bool:
        db = self._get_db()
        role = db.get_user_role(user_id)
        return check_permission(role, Permission.TRIGGER_NETWORK) if role else False

    def get_user_role(self, user_id: str) -> Optional[str]:
        db = self._get_db()
        return db.get_user_role(user_id)

    def create_user(self, user_id: str, role: str) -> bool:
        if role not in [r.value for r in Role]:
            return False
        db = self._get_db()
        db.create_user(user_id, role)
        return True


_rbac_enforcer: Optional[RBACEnforcer] = None


def get_rbac_enforcer() -> RBACEnforcer:
    global _rbac_enforcer
    if _rbac_enforcer is None:
        _rbac_enforcer = RBACEnforcer()
    return _rbac_enforcer
