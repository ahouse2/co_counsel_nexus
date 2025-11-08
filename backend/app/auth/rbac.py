from fastapi import Depends, HTTPException, status
from backend.app.auth.jwt import get_current_user
from backend.app.models.user import User as UserModel

def check_permissions(required_permissions: list[str]):
    def _check_permissions(current_user: UserModel = Depends(get_current_user)):
        user_permissions = []
        for role in current_user.roles:
            for permission in role.permissions:
                user_permissions.append(permission.name)

        if not all(permission in user_permissions for permission in required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized",
            )
        return current_user
    return _check_permissions
