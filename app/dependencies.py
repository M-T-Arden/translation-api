"""
Dependency injection functions for FastAPI
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from .database import get_db
from .auth import get_current_active_user
from .models import User

# Re-export commonly used dependencies
__all__ = ["get_db", "get_current_active_user"]

# You can add custom dependencies here, for example:

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Dependency to check if current user is an admin
    (You can add an 'is_admin' field to User model later)
    """
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Not enough permissions"
    #     )
    return current_user