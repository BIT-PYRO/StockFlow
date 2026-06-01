from fastapi import Depends, HTTPException, status
from app.models.user import User, UserRole
from app.auth.dependencies import get_current_active_user


class RoleChecker:
    """Dependency callable that enforces one or more allowed roles."""

    def __init__(self, allowed_roles: list[UserRole]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in self.allowed_roles]}",
            )
        return current_user


# ── Shorthand role checkers ───────────────────────────────────────────────────
require_admin = RoleChecker([UserRole.ADMIN])
require_manager_or_above = RoleChecker([UserRole.ADMIN, UserRole.MANAGER])
require_any_role = RoleChecker([UserRole.ADMIN, UserRole.MANAGER, UserRole.STAFF])


def require_roles(*roles: UserRole) -> RoleChecker:
    """Factory for one-off role requirements."""
    return RoleChecker(list(roles))
