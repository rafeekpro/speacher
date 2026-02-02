"""Authentication and authorization module"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from src.backend.models import ApiKeyDB, UserDB as ModelsUserDB
from src.backend.users_db import User as UsersDBUser, user_db as postgres_user_db

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Rate limiting storage (keep in-memory for now, could move to Redis later)
rate_limit_db: Dict[str, list] = {}


# Helper functions to convert between user database models
def _convert_postgres_user_to_model_user(user: UsersDBUser) -> ModelsUserDB:
    """Convert PostgreSQL user model to auth module UserDB model"""
    return ModelsUserDB(
        id=str(user.id),
        email=user.email,
        password_hash="",  # Not needed for auth operations
        full_name=user.full_name,
        role=user.role,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password meets complexity requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"

    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"

    return True, "Password is strong"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, user_id: str) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    # Store refresh token in database
    import asyncio
    try:
        asyncio.run(postgres_user_db.create_refresh_token(
            user_id=user_id,
            token=encoded_jwt,
            expires_at=expire
        ))
    except Exception as e:
        print(f"Warning: Failed to store refresh token in database: {e}")
        # Continue anyway - token is still valid

    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_user_by_email(email: str) -> Optional[ModelsUserDB]:
    """Get user by email from PostgreSQL database"""
    import asyncio
    user = await asyncio.run(postgres_user_db.get_user_by_email(email))
    if user:
        return _convert_postgres_user_to_model_user(user)
    return None


async def get_user_by_id(user_id: str) -> Optional[ModelsUserDB]:
    """Get user by ID from PostgreSQL database"""
    import asyncio
    user = await asyncio.run(postgres_user_db.get_user_by_id(user_id))
    if user:
        return _convert_postgres_user_to_model_user(user)
    return None


async def create_user(email: str, password: str, full_name: str, role: str = "user") -> ModelsUserDB:
    """Create a new user in PostgreSQL"""
    # Check if user exists
    existing_user = await get_user_by_email(email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with this email already exists")

    # Validate password
    is_valid, message = validate_password_strength(password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)

    # Create user in database
    import asyncio
    password_hash = hash_password(password)
    user = await asyncio.run(postgres_user_db.create_user(
        email=email,
        password_hash=password_hash,
        full_name=full_name,
        role=role
    ))

    return _convert_postgres_user_to_model_user(user)


async def authenticate_user(email: str, password: str) -> Optional[ModelsUserDB]:
    """Authenticate a user using PostgreSQL"""
    import asyncio
    user = await asyncio.run(postgres_user_db.verify_password_and_get_user(email, password))
    if user:
        return _convert_postgres_user_to_model_user(user)
    return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)) -> ModelsUserDB:
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = await get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
) -> Optional[ModelsUserDB]:
    """Get current user from JWT token or API key (optional).

    This function is for endpoints that support optional authentication.
    For required authentication, use get_current_user directly.

    Returns:
        ModelsUserDB if authenticated, None if no valid credentials provided.

    Note:
        This intentionally returns None instead of raising exceptions
        to support endpoints with optional authentication.
    """
    # Try JWT token first (preferred method)
    if credentials and credentials.credentials:
        try:
            return await get_current_user(credentials)
        except HTTPException:
            # Invalid JWT, but might have valid API key
            pass

    # Try API key as fallback
    if api_key:
        user = await get_user_by_api_key(api_key)
        if user:
            return user

    # No valid authentication provided - this is acceptable for optional auth
    return None


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
) -> ModelsUserDB:
    """Require authentication via JWT or API key.

    This function requires valid authentication and raises HTTPException if not provided.

    Raises:
        HTTPException: 401 if no valid authentication is provided.
    """
    user = await get_current_user_optional(credentials, api_key)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


async def create_api_key(user_id: str, name: str, expires_at: Optional[datetime] = None) -> tuple[str, ApiKeyDB]:
    """Create an API key for a user in PostgreSQL"""
    import asyncio
    key = secrets.token_urlsafe(32)
    api_key_response = await asyncio.run(postgres_user_db.create_api_key(
        user_id=user_id,
        name=name,
        key=key,
        expires_at=expires_at
    ))

    # Convert to ApiKeyDB model for backwards compatibility
    api_key_db = ApiKeyDB(
        id=api_key_response.id,
        user_id=api_key_response.user_id,
        name=api_key_response.name,
        key_hash=api_key_response.key_hash,
        last_used=api_key_response.last_used,
        created_at=api_key_response.created_at,
        expires_at=api_key_response.expires_at
    )

    return key, api_key_db


async def get_user_by_api_key(api_key: str) -> Optional[ModelsUserDB]:
    """Get user by API key from PostgreSQL"""
    import asyncio
    api_key_response = await asyncio.run(postgres_user_db.verify_api_key(api_key))
    if not api_key_response:
        return None

    # Update last used timestamp
    await asyncio.run(postgres_user_db.update_api_key_last_used(api_key))

    # Get and return user
    return await get_user_by_id(api_key_response.user_id)


async def revoke_refresh_token(token: str) -> bool:
    """Revoke a refresh token from PostgreSQL"""
    import asyncio
    return await asyncio.run(postgres_user_db.delete_refresh_token(token))


async def revoke_all_refresh_tokens(user_id: str) -> bool:
    """Revoke all refresh tokens for a user from PostgreSQL"""
    import asyncio
    return await asyncio.run(postgres_user_db.delete_user_refresh_tokens(user_id))


def check_rate_limit(identifier: str, max_attempts: int = 5, window_minutes: int = 15) -> bool:
    """Check if rate limit has been exceeded"""
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=window_minutes)

    if identifier not in rate_limit_db:
        rate_limit_db[identifier] = []

    # Clean old attempts
    rate_limit_db[identifier] = [attempt for attempt in rate_limit_db[identifier] if attempt > window_start]

    # Check limit
    if len(rate_limit_db[identifier]) >= max_attempts:
        return False

    # Record attempt
    rate_limit_db[identifier].append(now)
    return True


async def delete_user(user_id: str) -> bool:
    """Delete a user and all associated data from PostgreSQL"""
    import asyncio
    return await asyncio.run(postgres_user_db.delete_user(user_id))
