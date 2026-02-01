"""
Transcription database module for storing and retrieving transcriptions in PostgreSQL.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import create_engine, Column, String, Float, Integer, Boolean, DateTime, Text, Enum as SQLEnum, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.exc import SQLAlchemyError
from enum import Enum

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://speacher_user:SpeacherPro4_2024!@10.0.0.5:30432/speacher")

# SQLAlchemy setup
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Enum for transcription status - proper Python Enum
class TranscriptionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# SQLAlchemy model for Transcriptions
class Transcription(Base):
    __tablename__ = "transcriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audio_file_id = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    text = Column(Text, nullable=True)
    language = Column(String(10), default="en")
    confidence_score = Column(Float, nullable=True)
    word_count = Column(Integer, nullable=True)
    status = Column(SQLEnum(TranscriptionStatus), default=TranscriptionStatus.PENDING)
    engine = Column(String(50), default="whisper")
    engine_version = Column(String(50), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    meta_data = Column(JSONB, default=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format matching frontend expectations."""
        # Extract speakers from metadata if present
        speakers = self.meta_data.get("speakers", []) if self.meta_data else []

        return {
            "id": str(self.id),
            "audio_file_id": str(self.audio_file_id) if self.audio_file_id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "filename": self.meta_data.get("filename", "") if self.meta_data else "",
            "provider": self.meta_data.get("provider", "unknown") if self.meta_data else "unknown",
            "language": self.language,
            "transcript": self.text or "",
            "speakers": speakers,
            "enable_diarization": self.meta_data.get("enable_diarization", True) if self.meta_data else True,
            "max_speakers": self.meta_data.get("max_speakers", 4) if self.meta_data else 4,
            "duration": self.meta_data.get("duration", 0.0) if self.meta_data else 0.0,
            "cost_estimate": self.meta_data.get("cost_estimate", 0.0) if self.meta_data else 0.0,
            "confidence_score": float(self.confidence_score) if self.confidence_score is not None else None,
            "word_count": self.word_count,
            "status": self.status.value if hasattr(self.status, 'value') else str(self.status),
            "engine": self.engine,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "file_size": self.meta_data.get("file_size", 0) if self.meta_data else 0,
        }


class TranscriptionManager:
    """Manager for transcription database operations."""

    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url
        self.engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=3600)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()

    def save_transcription(
        self,
        filename: str,
        provider: str,
        language: str,
        transcript: str,
        speakers: List[Dict[str, Any]],
        enable_diarization: bool,
        max_speakers: int,
        duration: float,
        cost_estimate: float,
        file_size: int,
        confidence_score: Optional[float] = None,
        word_count: Optional[int] = None,
        processing_time_ms: Optional[int] = None,
        audio_file_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> Optional[str]:
        """
        Save a transcription to the database.

        Returns the transcription ID as a string, or None if save failed.
        """
        try:
            session = self.get_session()

            # Build metadata JSONB field
            metadata = {
                "filename": filename,
                "provider": provider,
                "enable_diarization": enable_diarization,
                "max_speakers": max_speakers,
                "duration": duration,
                "cost_estimate": cost_estimate,
                "file_size": file_size,
                "speakers": speakers,
            }

            transcription = Transcription(
                audio_file_id=audio_file_id,
                user_id=user_id,
                text=transcript,
                language=language,
                confidence_score=confidence_score,
                word_count=word_count,
                status=TranscriptionStatus.COMPLETED,
                engine=provider,
                processing_time_ms=processing_time_ms,
                completed_at=datetime.utcnow(),
                meta_data=metadata,
            )

            session.add(transcription)
            session.commit()
            session.refresh(transcription)

            transcription_id = str(transcription.id)
            session.close()

            return transcription_id

        except SQLAlchemyError as e:
            print(f"Error saving transcription: {e}")
            if session:
                session.rollback()
                session.close()
            return None

    def get_transcription_history(
        self,
        limit: int = 50,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        provider: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get transcription history with optional filtering.

        Args:
            limit: Maximum number of records to return
            search: Search term for filename
            date_from: Filter by date (inclusive)
            provider: Filter by provider

        Returns:
            List of transcription dictionaries
        """
        try:
            session = self.get_session()

            query = session.query(Transcription).filter(Transcription.status == TranscriptionStatus.COMPLETED)

            # Apply filters
            if search:
                # Search in filename within metadata
                query = query.filter(Transcription.meta_data["filename"].astext.ilike(f"%{search}%"))

            if date_from:
                query = query.filter(Transcription.created_at >= date_from)

            if provider:
                # Filter by provider within metadata
                query = query.filter(Transcription.meta_data["provider"].astext == provider)

            # Order by created_at descending and limit
            transcriptions = query.order_by(Transcription.created_at.desc()).limit(limit).all()

            result = [t.to_dict() for t in transcriptions]
            session.close()

            return result

        except SQLAlchemyError as e:
            print(f"Error fetching transcription history: {e}")
            if session:
                session.close()
            return []

    def get_transcription_by_id(self, transcription_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific transcription by ID.

        Args:
            transcription_id: UUID string

        Returns:
            Transcription dictionary or None if not found
        """
        try:
            session = self.get_session()

            # Convert string ID to UUID
            try:
                trans_uuid = UUID(transcription_id)
            except ValueError:
                session.close()
                return None

            transcription = session.query(Transcription).filter(Transcription.id == trans_uuid).first()

            if not transcription:
                session.close()
                return None

            result = transcription.to_dict()
            session.close()

            return result

        except SQLAlchemyError as e:
            print(f"Error fetching transcription: {e}")
            if session:
                session.close()
            return None

    def delete_transcription(self, transcription_id: str) -> bool:
        """
        Delete a transcription by ID.

        Args:
            transcription_id: UUID string

        Returns:
            True if deleted, False if not found
        """
        try:
            session = self.get_session()

            # Convert string ID to UUID
            try:
                trans_uuid = UUID(transcription_id)
            except ValueError:
                session.close()
                return False

            transcription = session.query(Transcription).filter(Transcription.id == trans_uuid).first()

            if not transcription:
                session.close()
                return False

            session.delete(transcription)
            session.commit()
            session.close()

            return True

        except SQLAlchemyError as e:
            print(f"Error deleting transcription: {e}")
            if session:
                session.rollback()
                session.close()
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get usage statistics.

        Returns:
            Dictionary with total count, provider stats, and recent files
        """
        try:
            session = self.get_session()

            # Total count
            total_count = session.query(func.count(Transcription.id)).filter(
                Transcription.status == TranscriptionStatus.COMPLETED
            ).scalar()

            # Provider statistics (aggregating from metadata)
            all_transcriptions = session.query(Transcription).filter(Transcription.status == TranscriptionStatus.COMPLETED).all()

            provider_stats = {}
            total_duration = 0.0
            total_cost = 0.0

            for t in all_transcriptions:
                provider = t.metadata.get("provider", "unknown") if t.metadata else "unknown"
                duration = t.metadata.get("duration", 0.0) if t.metadata else 0.0
                cost = t.metadata.get("cost_estimate", 0.0) if t.metadata else 0.0

                if provider not in provider_stats:
                    provider_stats[provider] = {"count": 0, "total_duration": 0.0, "total_cost": 0.0}

                provider_stats[provider]["count"] += 1
                provider_stats[provider]["total_duration"] += duration
                provider_stats[provider]["total_cost"] += cost

                total_duration += duration
                total_cost += cost

            # Convert to list format for compatibility
            provider_stats_list = [
                {
                    "_id": provider,
                    "count": stats["count"],
                    "total_duration": stats["total_duration"],
                    "total_cost": stats["total_cost"],
                }
                for provider, stats in provider_stats.items()
            ]

            # Recent files
            recent_transcriptions = (
                session.query(Transcription)
                .filter(Transcription.status == TranscriptionStatus.COMPLETED)
                .order_by(Transcription.created_at.desc())
                .limit(5)
                .all()
            )

            recent_files = [t.metadata.get("filename", "") if t.metadata else "" for t in recent_transcriptions]

            session.close()

            return {
                "total_transcriptions": total_count or 0,
                "provider_statistics": provider_stats_list,
                "recent_files": recent_files,
            }

        except SQLAlchemyError as e:
            print(f"Error fetching statistics: {e}")
            if session:
                session.close()
            return {
                "total_transcriptions": 0,
                "provider_statistics": [],
                "recent_files": [],
            }


# Global instance for use in main.py
transcription_manager = TranscriptionManager(DATABASE_URL)
