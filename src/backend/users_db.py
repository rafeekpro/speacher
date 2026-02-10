"""
User database module for storing and retrieving user data in PostgreSQL.
"""

import enum
import hashlib
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Text, create_engine, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Database URL from environment (required - no fallback for security)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable must be set")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# SQLAlchemy setup
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# SQLAlchemy Models
class UserRoleSQLEnum(str, enum.Enum):
    """User role enumeration for SQLAlchemy"""
    USER = "user"
    ADMIN = "admin"


class UserSQL(Base):
    """SQLAlchemy model for Users table"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="user", nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value if hasattr(self.role, 'value') else str(self.role),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ApiKeySQL(Base):
    """SQLAlchemy model for API Keys table"""
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(64), nullable=False, unique=True, index=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "key_hash": self.key_hash,
            "last_used": self.last_used,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


class RefreshTokenSQL(Base):
    """SQLAlchemy model for Refresh Tokens table"""
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    token = Column(Text, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "token": self.token,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
        }


# Pydantic Models for Response
class User(BaseModel):
    """Pydantic model for User responses"""
    id: str
    email: str
    full_name: str
    role: str
    created_at: datetime
    updated_at: datetime


class ApiKeyResponse(BaseModel):
    """Pydantic model for API Key responses"""
    id: str
    user_id: str
    name: str
    key_hash: str
    last_used: Optional[datetime]
    created_at: datetime
    expires_at: Optional[datetime]


class RefreshTokenResponse(BaseModel):
    """Pydantic model for Refresh Token responses"""
    id: str
    user_id: str
    token: str
    expires_at: datetime
    created_at: datetime


class UserDB:
    """User database operations using PostgreSQL"""

    def __init__(self, database_url: str = DATABASE_URL):
        """Initialize UserDB with database connection.

        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url
        self.engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=3600)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session.

        Returns:
            SQLAlchemy Session object
        """
        return self.SessionLocal()

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against

        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    def hash_api_key(self, api_key: str) -> str:
        """Hash an API key using SHA-256.

        Args:
            api_key: Plain text API key

        Returns:
            Hashed API key string
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    # User Operations

    async def create_user(
        self,
        email: str,
        password_hash: str,
        full_name: str,
        role: str = "user"
    ) -> User:
        """Create a new user in the database.

        Args:
            email: User email address (must be unique)
            password_hash: Bcrypt hashed password
            full_name: User's full name
            role: User role (default: "user")

        Returns:
            Created User object

        Raises:
            IntegrityError: If email already exists
            SQLAlchemyError: For other database errors
        """
        session = self.get_session()
        try:
            # Normalize role to lowercase
            role_value = role.lower() if role.lower() in ["user", "admin", "moderator"] else "user"

            user = UserSQL(
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                role=role_value
            )

            session.add(user)
            session.commit()
            session.refresh(user)

            result = User(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                role=user.role.value if hasattr(user.role, 'value') else str(user.role),
                created_at=user.created_at,
                updated_at=user.updated_at
            )

            session.close()
            return result

        except IntegrityError as e:
            session.rollback()
            session.close()
            if "email" in str(e.orig):
                raise IntegrityError("Duplicate email", e.params, e.orig)
            raise
        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            raise

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email address.

        Args:
            email: User email address

        Returns:
            User object if found, None otherwise
        """
        session = self.get_session()
        try:
            user = session.query(UserSQL).filter(UserSQL.email == email).first()

            if not user:
                session.close()
                return None

            result = User(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                role=user.role.value if hasattr(user.role, 'value') else str(user.role),
                created_at=user.created_at,
                updated_at=user.updated_at
            )

            session.close()
            return result

        except SQLAlchemyError as e:
            session.close()
            print(f"Error getting user by email: {e}")
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID.

        Args:
            user_id: User UUID as string

        Returns:
            User object if found, None otherwise
        """
        session = self.get_session()
        try:
            # Convert string ID to UUID
            try:
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                return None

            user = session.query(UserSQL).filter(UserSQL.id == user_uuid).first()

            if not user:
                session.close()
                return None

            result = User(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                role=user.role.value if hasattr(user.role, 'value') else str(user.role),
                created_at=user.created_at,
                updated_at=user.updated_at
            )

            session.close()
            return result

        except SQLAlchemyError as e:
            session.close()
            print(f"Error getting user by ID: {e}")
            return None

    async def verify_password_and_get_user(self, email: str, password: str) -> Optional[User]:
        """Verify user password and return user if valid.

        Args:
            email: User email address
            password: Plain text password to verify

        Returns:
            User object if password is correct, None otherwise
        """
        session = self.get_session()
        try:
            user = session.query(UserSQL).filter(UserSQL.email == email).first()

            if not user:
                session.close()
                return None

            if not self.verify_password(password, user.password_hash):
                session.close()
                return None

            result = User(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                role=user.role.value if hasattr(user.role, 'value') else str(user.role),
                created_at=user.created_at,
                updated_at=user.updated_at
            )

            session.close()
            return result

        except SQLAlchemyError as e:
            session.close()
            print(f"Error verifying password: {e}")
            return None

    async def update_user(self, user_id: str, **kwargs) -> Optional[User]:
        """Update user fields.

        Args:
            user_id: User UUID as string
            **kwargs: Fields to update (email, full_name, password_hash, role)

        Returns:
            Updated User object if found, None otherwise
        """
        session = self.get_session()
        try:
            # Convert string ID to UUID
            try:
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                return None

            user = session.query(UserSQL).filter(UserSQL.id == user_uuid).first()

            if not user:
                session.close()
                return None

            # Update allowed fields
            allowed_fields = {"email", "full_name", "password_hash", "role"}
            for key, value in kwargs.items():
                if key in allowed_fields and value is not None:
                    if key == "role":
                        # Convert string role to enum
                        user.role = UserRoleSQLEnum.ADMIN if value == "admin" else UserRoleSQLEnum.USER
                    else:
                        setattr(user, key, value)

            user.updated_at = datetime.utcnow()

            session.commit()
            session.refresh(user)

            result = User(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                role=user.role.value if hasattr(user.role, 'value') else str(user.role),
                created_at=user.created_at,
                updated_at=user.updated_at
            )

            session.close()
            return result

        except IntegrityError as e:
            session.rollback()
            session.close()
            if "email" in str(e.orig):
                raise IntegrityError("Duplicate email", e.params, e.orig)
            raise
        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            print(f"Error updating user: {e}")
            return None

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user and all associated data.

        Args:
            user_id: User UUID as string

        Returns:
            True if deleted, False if not found
        """
        session = self.get_session()
        try:
            # Convert string ID to UUID
            try:
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                return False

            user = session.query(UserSQL).filter(UserSQL.id == user_uuid).first()

            if not user:
                session.close()
                return False

            # Delete associated refresh tokens
            session.query(RefreshTokenSQL).filter(RefreshTokenSQL.user_id == user_uuid).delete()

            # Delete associated API keys
            session.query(ApiKeySQL).filter(ApiKeySQL.user_id == user_uuid).delete()

            # Delete user
            session.delete(user)
            session.commit()
            session.close()

            return True

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            print(f"Error deleting user: {e}")
            return False

    # API Key Operations

    async def create_api_key(
        self,
        user_id: str,
        name: str,
        key: str,
        expires_at: Optional[datetime] = None
    ) -> ApiKeyResponse:
        """Create an API key for a user.

        Args:
            user_id: User UUID as string
            name: API key name/label
            key: Plain text API key (will be hashed)
            expires_at: Optional expiration datetime

        Returns:
            Created ApiKey object

        Raises:
            SQLAlchemyError: For database errors
        """
        session = self.get_session()
        try:
            # Convert string ID to UUID
            try:
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                raise ValueError("Invalid user_id format")

            key_hash = self.hash_api_key(key)

            api_key = ApiKeySQL(
                user_id=user_uuid,
                name=name,
                key_hash=key_hash,
                expires_at=expires_at
            )

            session.add(api_key)
            session.commit()
            session.refresh(api_key)

            result = ApiKeyResponse(
                id=str(api_key.id),
                user_id=str(api_key.user_id),
                name=api_key.name,
                key_hash=api_key.key_hash,
                last_used=api_key.last_used,
                created_at=api_key.created_at,
                expires_at=api_key.expires_at
            )

            session.close()
            return result

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            raise

    async def get_api_keys(self, user_id: str) -> List[ApiKeyResponse]:
        """Get all API keys for a user.

        Args:
            user_id: User UUID as string

        Returns:
            List of ApiKey objects
        """
        session = self.get_session()
        try:
            # Convert string ID to UUID
            try:
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                return []

            api_keys = session.query(ApiKeySQL).filter(ApiKeySQL.user_id == user_uuid).all()

            result = [
                ApiKeyResponse(
                    id=str(key.id),
                    user_id=str(key.user_id),
                    name=key.name,
                    key_hash=key.key_hash,
                    last_used=key.last_used,
                    created_at=key.created_at,
                    expires_at=key.expires_at
                )
                for key in api_keys
            ]

            session.close()
            return result

        except SQLAlchemyError as e:
            session.close()
            print(f"Error getting API keys: {e}")
            return []

    async def verify_api_key(self, key: str) -> Optional[ApiKeyResponse]:
        """Verify an API key and return the key record if valid.

        Args:
            key: Plain text API key to verify

        Returns:
            ApiKey object if valid and not expired, None otherwise
        """
        session = self.get_session()
        try:
            key_hash = self.hash_api_key(key)

            api_key = session.query(ApiKeySQL).filter(ApiKeySQL.key_hash == key_hash).first()

            if not api_key:
                session.close()
                return None

            # Check expiration
            if api_key.expires_at and api_key.expires_at < datetime.utcnow():
                session.close()
                return None

            result = ApiKeyResponse(
                id=str(api_key.id),
                user_id=str(api_key.user_id),
                name=api_key.name,
                key_hash=api_key.key_hash,
                last_used=api_key.last_used,
                created_at=api_key.created_at,
                expires_at=api_key.expires_at
            )

            session.close()
            return result

        except SQLAlchemyError as e:
            session.close()
            print(f"Error verifying API key: {e}")
            return None

    async def update_api_key_last_used(self, key: str) -> bool:
        """Update the last_used timestamp for an API key.

        Args:
            key: Plain text API key

        Returns:
            True if updated, False if key not found
        """
        session = self.get_session()
        try:
            key_hash = self.hash_api_key(key)

            api_key = session.query(ApiKeySQL).filter(ApiKeySQL.key_hash == key_hash).first()

            if not api_key:
                session.close()
                return False

            # Check expiration
            if api_key.expires_at and api_key.expires_at < datetime.utcnow():
                session.close()
                return False

            api_key.last_used = datetime.utcnow()
            session.commit()
            session.close()

            return True

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            print(f"Error updating API key last used: {e}")
            return False

    async def delete_api_key(self, api_key_id: str, user_id: str) -> bool:
        """Delete an API key.

        Args:
            api_key_id: API Key UUID as string
            user_id: User UUID as string (for authorization)

        Returns:
            True if deleted, False if not found
        """
        session = self.get_session()
        try:
            # Convert strings to UUIDs
            try:
                key_uuid = UUID(api_key_id)
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                return False

            api_key = session.query(ApiKeySQL).filter(
                ApiKeySQL.id == key_uuid,
                ApiKeySQL.user_id == user_uuid
            ).first()

            if not api_key:
                session.close()
                return False

            session.delete(api_key)
            session.commit()
            session.close()

            return True

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            print(f"Error deleting API key: {e}")
            return False

    # Refresh Token Operations

    async def create_refresh_token(
        self,
        user_id: str,
        token: str,
        expires_at: datetime
    ) -> RefreshTokenResponse:
        """Create a refresh token for a user.

        Args:
            user_id: User UUID as string
            token: Refresh token string
            expires_at: Token expiration datetime

        Returns:
            Created RefreshToken object

        Raises:
            SQLAlchemyError: For database errors
        """
        session = self.get_session()
        try:
            # Convert string ID to UUID
            try:
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                raise ValueError("Invalid user_id format")

            refresh_token = RefreshTokenSQL(
                user_id=user_uuid,
                token=token,
                expires_at=expires_at
            )

            session.add(refresh_token)
            session.commit()
            session.refresh(refresh_token)

            result = RefreshTokenResponse(
                id=str(refresh_token.id),
                user_id=str(refresh_token.user_id),
                token=refresh_token.token,
                expires_at=refresh_token.expires_at,
                created_at=refresh_token.created_at
            )

            session.close()
            return result

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            raise

    async def verify_refresh_token(self, token: str) -> Optional[RefreshTokenResponse]:
        """Verify a refresh token and return the token record if valid.

        Args:
            token: Refresh token string

        Returns:
            RefreshToken object if valid and not expired, None otherwise
        """
        session = self.get_session()
        try:
            refresh_token = session.query(RefreshTokenSQL).filter(RefreshTokenSQL.token == token).first()

            if not refresh_token:
                session.close()
                return None

            # Check expiration
            if refresh_token.expires_at < datetime.utcnow():
                session.close()
                return None

            result = RefreshTokenResponse(
                id=str(refresh_token.id),
                user_id=str(refresh_token.user_id),
                token=refresh_token.token,
                expires_at=refresh_token.expires_at,
                created_at=refresh_token.created_at
            )

            session.close()
            return result

        except SQLAlchemyError as e:
            session.close()
            print(f"Error verifying refresh token: {e}")
            return None

    async def delete_refresh_token(self, token: str) -> bool:
        """Delete a refresh token.

        Args:
            token: Refresh token string

        Returns:
            True if deleted, False if not found
        """
        session = self.get_session()
        try:
            refresh_token = session.query(RefreshTokenSQL).filter(RefreshTokenSQL.token == token).first()

            if not refresh_token:
                session.close()
                return False

            session.delete(refresh_token)
            session.commit()
            session.close()

            return True

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            print(f"Error deleting refresh token: {e}")
            return False

    async def delete_user_refresh_tokens(self, user_id: str) -> bool:
        """Delete all refresh tokens for a user.

        Args:
            user_id: User UUID as string

        Returns:
            True if any were deleted, False if user not found or no tokens
        """
        session = self.get_session()
        try:
            # Convert string ID to UUID
            try:
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                return False

            count = session.query(RefreshTokenSQL).filter(RefreshTokenSQL.user_id == user_uuid).delete()

            session.commit()
            session.close()

            return count > 0

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            print(f"Error deleting user refresh tokens: {e}")
            return False


# Global instance for use in main.py
user_db = UserDB(DATABASE_URL)
