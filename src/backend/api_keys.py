"""API Keys management module for storing provider credentials in PostgreSQL."""

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet
import base64
import hashlib
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, JSON
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://speacher_user:SpeacherPro4_2024!@10.0.0.5:30432/speacher")

# SQLAlchemy setup
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# SQLAlchemy model for API Keys
class APIKey(Base):
    __tablename__ = "api_keys"

    provider = Column(String(50), primary_key=True)
    keys = Column(JSON, nullable=True)
    enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "provider": self.provider,
            "keys": self.keys,
            "enabled": self.enabled,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class APIKeysManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=3600)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Create tables
        Base.metadata.create_all(self.engine)

        # Generate or load encryption key
        self.cipher_suite = self._get_cipher()

    def _get_cipher(self) -> Fernet:
        """Get or create encryption cipher for API keys."""
        master_key = os.getenv("ENCRYPTION_KEY")
        if not master_key:
            master_key = "speacher-default-encryption-key-change-in-production"

        key = base64.urlsafe_b64encode(hashlib.sha256(master_key.encode()).digest())
        return Fernet(key)

    def encrypt_value(self, value: str) -> str:
        """Encrypt a value."""
        if not value:
            return ""
        return self.cipher_suite.encrypt(value.encode()).decode()

    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a value."""
        if not encrypted_value:
            return ""
        try:
            return self.cipher_suite.decrypt(encrypted_value.encode()).decode()
        except Exception:
            return ""

    def save_api_keys(self, provider: str, keys: Dict[str, Any]) -> bool:
        """Save or update API keys for a provider."""
        try:
            session = self.SessionLocal()

            # Encrypt sensitive values
            encrypted_keys = {}
            for key, value in keys.items():
                if value and any(sensitive in key.lower() for sensitive in ["key", "secret", "token", "password"]):
                    encrypted_keys[key] = self.encrypt_value(str(value))
                else:
                    encrypted_keys[key] = value

            # Check if provider exists
            api_key = session.query(APIKey).filter_by(provider=provider).first()

            if api_key:
                api_key.keys = encrypted_keys
                api_key.enabled = True
                api_key.updated_at = datetime.utcnow()
            else:
                api_key = APIKey(provider=provider, keys=encrypted_keys, enabled=True, updated_at=datetime.utcnow())
                session.add(api_key)

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error saving API keys: {e}")
            return False

    def get_api_keys(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get decrypted API keys for a provider."""
        session = self.SessionLocal()

        try:
            api_key = session.query(APIKey).filter_by(provider=provider).first()

            if not api_key:
                return None

            # Decrypt sensitive values
            decrypted_keys = {}
            for key, value in api_key.to_dict().get("keys", {}).items():
                if value and any(sensitive in key.lower() for sensitive in ["key", "secret", "token", "password"]):
                    try:
                        decrypted_keys[key] = self.decrypt_value(value)
                    except Exception:
                        decrypted_keys[key] = value
                else:
                    decrypted_keys[key] = value

            # Check if provider is properly configured
            is_configured = self.validate_provider_config(api_key.provider, decrypted_keys)

            return {
                "provider": api_key.provider,
                "keys": decrypted_keys,
                "enabled": api_key.enabled,
                "configured": is_configured,
                "updated_at": api_key.updated_at.isoformat() if api_key.updated_at else None,
            }
        except Exception as e:
            print(f"Error getting API keys from PostgreSQL: {e}")
            return None

    def _get_env_keys(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get API keys from environment variables."""
        if provider == "aws":
            access_key = os.getenv("AWS_ACCESS_KEY_ID")
            secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            if access_key and secret_key:
                keys = {
                    "access_key_id": access_key,
                    "secret_access_key": secret_key,
                    "region": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
                    "s3_bucket_name": os.getenv("S3_BUCKET_NAME", "speacher-rafal-app"),
                }
                return {
                    "provider": "aws",
                    "keys": keys,
                    "enabled": True,
                    "configured": self.validate_provider_config("aws", keys),
                    "updated_at": None,
                }
        elif provider == "azure":
            subscription_key = os.getenv("AZURE_SPEECH_KEY")
            if subscription_key:
                keys = {"subscription_key": subscription_key, "region": os.getenv("AZURE_SPEECH_REGION", "eastus")}
                return {
                    "provider": "azure",
                    "keys": keys,
                    "enabled": True,
                    "configured": self.validate_provider_config("azure", keys),
                    "updated_at": None,
                }
        elif provider == "gcp":
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if credentials_path and os.path.exists(credentials_path):
                import json

                with open(credentials_path, "r") as f:
                    keys = {
                        "credentials_json": f.read(),
                        "project_id": os.getenv("GCP_PROJECT_ID"),
                        "gcs_bucket_name": os.getenv("GCP_BUCKET_NAME", "speacher-gcp"),
                    }
                return {
                    "provider": "gcp",
                    "keys": keys,
                    "enabled": True,
                    "configured": self.validate_provider_config("gcp", keys),
                    "updated_at": None,
                }

        return None

    def validate_provider_config(self, provider: str, keys: Dict[str, Any]) -> bool:
        """Validate that all required keys are present and not empty for a provider."""
        required_keys = {
            "aws": ["access_key_id", "secret_access_key", "region", "s3_bucket_name"],
            "azure": ["subscription_key", "region"],
            "gcp": ["credentials_json", "project_id", "gcs_bucket_name"],
        }

        if provider not in required_keys:
            return False

        for key in required_keys[provider]:
            if key not in keys or not keys[key] or str(keys[key]).strip() == "":
                return False

        return True

    def get_all_providers(self) -> list:
        """Get all configured providers with their status."""
        session = self.SessionLocal()

        try:
            providers = []
            for doc in session.query(APIKey).filter_by(enabled=True).all():
                decrypted_keys = {}
                for key, value in doc.to_dict().get("keys", {}).items():
                    if value and any(sensitive in key.lower() for sensitive in ["key", "secret", "token", "password"]):
                        try:
                            decrypted_keys[key] = self.decrypt_value(value)
                        except Exception:
                            decrypted_keys[key] = value
                    else:
                        decrypted_keys[key] = value

                is_properly_configured = self.validate_provider_config(doc.provider, decrypted_keys)

                providers.append(
                    {
                        "provider": doc.provider,
                        "enabled": doc.enabled,
                        "configured": is_properly_configured and doc.enabled,
                        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                        "source": "postgresql",
                    }
                )

            # Add environment-only providers
            for provider in ["aws", "azure", "gcp"]:
                env_keys = self._get_env_keys(provider)
                if env_keys:
                    providers.append(env_keys)
                else:
                    providers.append(
                        {
                            "provider": provider,
                            "enabled": False,
                            "configured": False,
                            "updated_at": None,
                            "source": "environment",
                        }
                    )

            return providers
        except Exception as e:
            print(f"Error getting providers from PostgreSQL, using environment fallback: {e}")
            # Fallback to environment-only mode
            providers = []
            for provider in ["aws", "azure", "gcp"]:
                env_keys = self._get_env_keys(provider)
                if env_keys:
                    providers.append(env_keys)
                else:
                    providers.append(
                        {
                            "provider": provider,
                            "enabled": False,
                            "configured": False,
                            "updated_at": None,
                            "source": "environment",
                        }
                    )
            return providers

    def delete_api_keys(self, provider: str) -> bool:
        """Delete API keys for a provider."""
        try:
            session = self.SessionLocal()
            result = session.query(APIKey).filter_by(provider=provider).delete()
            session.commit()
            return result > 0
        except Exception as e:
            session.rollback()
            print(f"Error deleting API keys: {e}")
            return False

    def toggle_provider(self, provider: str, enabled: bool) -> bool:
        """Enable or disable a provider."""
        try:
            session = self.SessionLocal()
            api_key = session.query(APIKey).filter_by(provider=provider).first()

            if api_key:
                api_key.enabled = enabled
                api_key.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Error toggling provider: {e}")
            return False
