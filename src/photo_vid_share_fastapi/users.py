import uuid
from typing import Optional
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, models
from fastapi_users.authentication import (
  AuthenticationBackend,
  BearerTransport,
  JWTStrategy,
)

from fastapi_users.db import SQLAlchemyUserDatabase
from .db import User, get_user_db



SECRET = "vsafcfvnbhvg543fvvascvgf"  # In production, use a secure secret key and store it in an environment variable

# Define the authentication backend
class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    user_db_model = User
    # Define the methods for user management
    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")
    # Define the methods for user management
    async def on_after_forgot_password(self, user: User, token: str, request: Optional[Request] = None):
        print(f"User {user.id} has forgot their password. Reset token: {token}")
    # Define the methods for user management
    async def on_after_request_verify(self, user: User, token: str, request: Optional[Request] = None):
        print(f"Verification requested for user {user.id}. Verification token: {token}")

# Define the dependency to get the user manager
async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)
# Define the JWT strategy for authentication
bearer_transport = BearerTransport(tokenUrl="/auth/jwt/login")

# Define the JWT strategy for authentication
def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)

# Define the authentication backend
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# Create the FastAPIUsers instance
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

# Define the current active user dependency
current_active_user = fastapi_users.current_user(active=True)