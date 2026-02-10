"""
Project database module for storing and retrieving project/recording data in PostgreSQL.
"""

import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, Integer, Float, Text, create_engine, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

# Database URL from environment (required - no fallback for security)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable must be set")

# SQLAlchemy setup
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# SQLAlchemy Models
class ProjectStatusSQLEnum(str, enum):
    """Project status enumeration for SQLAlchemy"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


import enum


class Project(Base):
    """SQLAlchemy model for Projects table"""
    __tablename__ = "projects"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default=ProjectStatusSQLEnum.ACTIVE, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    recordings = relationship("Recording", back_populates="project", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="project", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class Recording(Base):
    """SQLAlchemy model for Recordings table"""
    __tablename__ = "recordings"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    filename = Column(String(500), nullable=False)
    duration = Column(Float, nullable=True)
    file_size = Column(Integer, nullable=True)
    status = Column(String(50), default="pending", nullable=False)
    transcription = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="recordings")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "user_id": str(self.user_id),
            "filename": self.filename,
            "duration": self.duration,
            "file_size": self.file_size,
            "status": self.status,
            "transcription": self.transcription,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class Tag(Base):
    """SQLAlchemy model for Tags table"""
    __tablename__ = "tags"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    color = Column(String(20), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="tags")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "name": self.name,
            "color": self.color,
        }


# Pydantic Models for Response
class Project(BaseModel):
    """Pydantic model for Project responses"""
    id: str
    user_id: str
    name: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime


class Recording(BaseModel):
    """Pydantic model for Recording responses"""
    id: str
    project_id: str
    user_id: str
    filename: str
    duration: Optional[float]
    file_size: Optional[int]
    status: str
    transcription: Optional[str]
    created_at: datetime
    updated_at: datetime


class Tag(BaseModel):
    """Pydantic model for Tag responses"""
    id: str
    project_id: str
    name: str
    color: Optional[str]


class ProjectDB:
    """Project and recording database operations using PostgreSQL"""

    def __init__(self, database_url: str = DATABASE_URL):
        """Initialize ProjectDB with database connection.

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

    # Project Operations

    async def create_project(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        status: str = "active"
    ) -> Project:
        """Create a new project in the database.

        Args:
            user_id: User UUID as string
            name: Project name
            description: Optional project description
            status: Project status (default: "active")

        Returns:
            Created Project object

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

            project = Project(
                user_id=user_uuid,
                name=name,
                description=description,
                status=status
            )

            session.add(project)
            session.commit()
            session.refresh(project)

            result = Project(
                id=str(project.id),
                user_id=str(project.user_id),
                name=project.name,
                description=project.description,
                status=project.status,
                created_at=project.created_at,
                updated_at=project.updated_at
            )

            session.close()
            return result

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            raise

    async def get_project(self, project_id: str, user_id: str) -> Optional[Project]:
        """Get a project by ID with user isolation.

        Args:
            project_id: Project UUID as string
            user_id: User UUID as string (for authorization)

        Returns:
            Project object if found and belongs to user, None otherwise
        """
        session = self.get_session()
        try:
            # Convert strings to UUIDs
            try:
                project_uuid = UUID(project_id)
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                return None

            project = session.query(Project).filter(
                Project.id == project_uuid,
                Project.user_id == user_uuid
            ).first()

            if not project:
                session.close()
                return None

            result = Project(
                id=str(project.id),
                user_id=str(project.user_id),
                name=project.name,
                description=project.description,
                status=project.status,
                created_at=project.created_at,
                updated_at=project.updated_at
            )

            session.close()
            return result

        except SQLAlchemyError as e:
            session.close()
            print(f"Error getting project: {e}")
            return None

    async def list_projects(
        self,
        user_id: str,
        status: Optional[str] = None
    ) -> List[Project]:
        """List all projects for a user with optional status filtering.

        Args:
            user_id: User UUID as string
            status: Optional status filter

        Returns:
            List of Project objects
        """
        session = self.get_session()
        try:
            # Convert string ID to UUID
            try:
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                return []

            query = session.query(Project).filter(Project.user_id == user_uuid)

            if status:
                query = query.filter(Project.status == status)

            projects = query.order_by(Project.created_at.desc()).all()

            result = [
                Project(
                    id=str(project.id),
                    user_id=str(project.user_id),
                    name=project.name,
                    description=project.description,
                    status=project.status,
                    created_at=project.created_at,
                    updated_at=project.updated_at
                )
                for project in projects
            ]

            session.close()
            return result

        except SQLAlchemyError as e:
            session.close()
            print(f"Error listing projects: {e}")
            return []

    async def update_project(
        self,
        project_id: str,
        user_id: str,
        **kwargs
    ) -> Optional[Project]:
        """Update project fields with user isolation.

        Args:
            project_id: Project UUID as string
            user_id: User UUID as string (for authorization)
            **kwargs: Fields to update (name, description, status)

        Returns:
            Updated Project object if found and authorized, None otherwise
        """
        session = self.get_session()
        try:
            # Convert strings to UUIDs
            try:
                project_uuid = UUID(project_id)
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                return None

            project = session.query(Project).filter(
                Project.id == project_uuid,
                Project.user_id == user_uuid
            ).first()

            if not project:
                session.close()
                return None

            # Update allowed fields
            allowed_fields = {"name", "description", "status"}
            for key, value in kwargs.items():
                if key in allowed_fields and value is not None:
                    setattr(project, key, value)

            project.updated_at = datetime.utcnow()

            session.commit()
            session.refresh(project)

            result = Project(
                id=str(project.id),
                user_id=str(project.user_id),
                name=project.name,
                description=project.description,
                status=project.status,
                created_at=project.created_at,
                updated_at=project.updated_at
            )

            session.close()
            return result

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            print(f"Error updating project: {e}")
            return None

    async def delete_project(self, project_id: str, user_id: str) -> bool:
        """Delete a project and all associated recordings/tags with user isolation.

        Args:
            project_id: Project UUID as string
            user_id: User UUID as string (for authorization)

        Returns:
            True if deleted, False if not found or unauthorized
        """
        session = self.get_session()
        try:
            # Convert strings to UUIDs
            try:
                project_uuid = UUID(project_id)
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                return False

            project = session.query(Project).filter(
                Project.id == project_uuid,
                Project.user_id == user_uuid
            ).first()

            if not project:
                session.close()
                return False

            # Delete project (cascade will handle recordings and tags)
            session.delete(project)
            session.commit()
            session.close()

            return True

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            print(f"Error deleting project: {e}")
            return False

    # Recording Operations

    async def create_recording(
        self,
        project_id: str,
        user_id: str,
        filename: str,
        **kwargs
    ) -> Recording:
        """Create a new recording in the database.

        Args:
            project_id: Project UUID as string
            user_id: User UUID as string
            filename: Recording filename
            **kwargs: Optional fields (duration, file_size, status)

        Returns:
            Created Recording object

        Raises:
            ValueError: If project_id or user_id format is invalid
            SQLAlchemyError: For database errors
        """
        session = self.get_session()
        try:
            # Convert strings to UUIDs
            try:
                project_uuid = UUID(project_id)
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                raise ValueError("Invalid project_id or user_id format")

            # Verify project exists and belongs to user
            project = session.query(Project).filter(
                Project.id == project_uuid,
                Project.user_id == user_uuid
            ).first()

            if not project:
                session.close()
                raise ValueError("Project not found or unauthorized")

            recording = Recording(
                project_id=project_uuid,
                user_id=user_uuid,
                filename=filename,
                duration=kwargs.get("duration"),
                file_size=kwargs.get("file_size"),
                status=kwargs.get("status", "pending")
            )

            session.add(recording)
            session.commit()
            session.refresh(recording)

            result = Recording(
                id=str(recording.id),
                project_id=str(recording.project_id),
                user_id=str(recording.user_id),
                filename=recording.filename,
                duration=recording.duration,
                file_size=recording.file_size,
                status=recording.status,
                transcription=recording.transcription,
                created_at=recording.created_at,
                updated_at=recording.updated_at
            )

            session.close()
            return result

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            raise

    async def get_recording(self, recording_id: str, user_id: str) -> Optional[Recording]:
        """Get a recording by ID with user isolation.

        Args:
            recording_id: Recording UUID as string
            user_id: User UUID as string (for authorization)

        Returns:
            Recording object if found and authorized, None otherwise
        """
        session = self.get_session()
        try:
            # Convert strings to UUIDs
            try:
                recording_uuid = UUID(recording_id)
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                return None

            recording = session.query(Recording).filter(
                Recording.id == recording_uuid,
                Recording.user_id == user_uuid
            ).first()

            if not recording:
                session.close()
                return None

            result = Recording(
                id=str(recording.id),
                project_id=str(recording.project_id),
                user_id=str(recording.user_id),
                filename=recording.filename,
                duration=recording.duration,
                file_size=recording.file_size,
                status=recording.status,
                transcription=recording.transcription,
                created_at=recording.created_at,
                updated_at=recording.updated_at
            )

            session.close()
            return result

        except SQLAlchemyError as e:
            session.close()
            print(f"Error getting recording: {e}")
            return None

    async def list_recordings(self, project_id: str, user_id: str) -> List[Recording]:
        """List all recordings for a project with user isolation.

        Args:
            project_id: Project UUID as string
            user_id: User UUID as string (for authorization)

        Returns:
            List of Recording objects
        """
        session = self.get_session()
        try:
            # Convert strings to UUIDs
            try:
                project_uuid = UUID(project_id)
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                return []

            # Verify project exists and belongs to user
            project = session.query(Project).filter(
                Project.id == project_uuid,
                Project.user_id == user_uuid
            ).first()

            if not project:
                session.close()
                return []

            recordings = session.query(Recording).filter(
                Recording.project_id == project_uuid
            ).order_by(Recording.created_at.desc()).all()

            result = [
                Recording(
                    id=str(recording.id),
                    project_id=str(recording.project_id),
                    user_id=str(recording.user_id),
                    filename=recording.filename,
                    duration=recording.duration,
                    file_size=recording.file_size,
                    status=recording.status,
                    transcription=recording.transcription,
                    created_at=recording.created_at,
                    updated_at=recording.updated_at
                )
                for recording in recordings
            ]

            session.close()
            return result

        except SQLAlchemyError as e:
            session.close()
            print(f"Error listing recordings: {e}")
            return []

    async def update_recording(
        self,
        recording_id: str,
        user_id: str,
        **kwargs
    ) -> Optional[Recording]:
        """Update recording fields with user isolation.

        Args:
            recording_id: Recording UUID as string
            user_id: User UUID as string (for authorization)
            **kwargs: Fields to update (filename, duration, file_size, status, transcription)

        Returns:
            Updated Recording object if found and authorized, None otherwise
        """
        session = self.get_session()
        try:
            # Convert strings to UUIDs
            try:
                recording_uuid = UUID(recording_id)
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                return None

            recording = session.query(Recording).filter(
                Recording.id == recording_uuid,
                Recording.user_id == user_uuid
            ).first()

            if not recording:
                session.close()
                return None

            # Update allowed fields
            allowed_fields = {"filename", "duration", "file_size", "status", "transcription"}
            for key, value in kwargs.items():
                if key in allowed_fields and value is not None:
                    setattr(recording, key, value)

            recording.updated_at = datetime.utcnow()

            session.commit()
            session.refresh(recording)

            result = Recording(
                id=str(recording.id),
                project_id=str(recording.project_id),
                user_id=str(recording.user_id),
                filename=recording.filename,
                duration=recording.duration,
                file_size=recording.file_size,
                status=recording.status,
                transcription=recording.transcription,
                created_at=recording.created_at,
                updated_at=recording.updated_at
            )

            session.close()
            return result

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            print(f"Error updating recording: {e}")
            return None

    async def delete_recording(self, recording_id: str, user_id: str) -> bool:
        """Delete a recording with user isolation.

        Args:
            recording_id: Recording UUID as string
            user_id: User UUID as string (for authorization)

        Returns:
            True if deleted, False if not found or unauthorized
        """
        session = self.get_session()
        try:
            # Convert strings to UUIDs
            try:
                recording_uuid = UUID(recording_id)
                user_uuid = UUID(user_id)
            except ValueError:
                session.close()
                return False

            recording = session.query(Recording).filter(
                Recording.id == recording_uuid,
                Recording.user_id == user_uuid
            ).first()

            if not recording:
                session.close()
                return False

            session.delete(recording)
            session.commit()
            session.close()

            return True

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            print(f"Error deleting recording: {e}")
            return False

    async def update_recording_status(self, recording_id: str, status: str) -> bool:
        """Update recording status (bypasses user check for internal use).

        Args:
            recording_id: Recording UUID as string
            status: New status value

        Returns:
            True if updated, False if not found
        """
        session = self.get_session()
        try:
            # Convert string ID to UUID
            try:
                recording_uuid = UUID(recording_id)
            except ValueError:
                session.close()
                return False

            recording = session.query(Recording).filter(
                Recording.id == recording_uuid
            ).first()

            if not recording:
                session.close()
                return False

            recording.status = status
            recording.updated_at = datetime.utcnow()

            session.commit()
            session.close()

            return True

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            print(f"Error updating recording status: {e}")
            return False

    async def update_recording_transcription(self, recording_id: str, transcription: str) -> bool:
        """Update recording transcription (bypasses user check for internal use).

        Args:
            recording_id: Recording UUID as string
            transcription: Transcription text

        Returns:
            True if updated, False if not found
        """
        session = self.get_session()
        try:
            # Convert string ID to UUID
            try:
                recording_uuid = UUID(recording_id)
            except ValueError:
                session.close()
                return False

            recording = session.query(Recording).filter(
                Recording.id == recording_uuid
            ).first()

            if not recording:
                session.close()
                return False

            recording.transcription = transcription
            recording.updated_at = datetime.utcnow()

            session.commit()
            session.close()

            return True

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            print(f"Error updating recording transcription: {e}")
            return False

    # Tag Operations

    async def create_tag(
        self,
        project_id: str,
        name: str,
        color: Optional[str] = None
    ) -> Tag:
        """Create a new tag for a project.

        Args:
            project_id: Project UUID as string
            name: Tag name
            color: Optional color value

        Returns:
            Created Tag object

        Raises:
            ValueError: If project_id format is invalid
            SQLAlchemyError: For database errors
        """
        session = self.get_session()
        try:
            # Convert string ID to UUID
            try:
                project_uuid = UUID(project_id)
            except ValueError:
                session.close()
                raise ValueError("Invalid project_id format")

            tag = Tag(
                project_id=project_uuid,
                name=name,
                color=color
            )

            session.add(tag)
            session.commit()
            session.refresh(tag)

            result = Tag(
                id=str(tag.id),
                project_id=str(tag.project_id),
                name=tag.name,
                color=tag.color
            )

            session.close()
            return result

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            raise

    async def list_tags(self, project_id: str) -> List[Tag]:
        """List all tags for a project.

        Args:
            project_id: Project UUID as string

        Returns:
            List of Tag objects
        """
        session = self.get_session()
        try:
            # Convert string ID to UUID
            try:
                project_uuid = UUID(project_id)
            except ValueError:
                session.close()
                return []

            tags = session.query(Tag).filter(
                Tag.project_id == project_uuid
            ).order_by(Tag.name).all()

            result = [
                Tag(
                    id=str(tag.id),
                    project_id=str(tag.project_id),
                    name=tag.name,
                    color=tag.color
                )
                for tag in tags
            ]

            session.close()
            return result

        except SQLAlchemyError as e:
            session.close()
            print(f"Error listing tags: {e}")
            return []

    async def delete_tag(self, tag_id: str, project_id: str) -> bool:
        """Delete a tag with project isolation.

        Args:
            tag_id: Tag UUID as string
            project_id: Project UUID as string (for authorization)

        Returns:
            True if deleted, False if not found or unauthorized
        """
        session = self.get_session()
        try:
            # Convert strings to UUIDs
            try:
                tag_uuid = UUID(tag_id)
                project_uuid = UUID(project_id)
            except ValueError:
                session.close()
                return False

            tag = session.query(Tag).filter(
                Tag.id == tag_uuid,
                Tag.project_id == project_uuid
            ).first()

            if not tag:
                session.close()
                return False

            session.delete(tag)
            session.commit()
            session.close()

            return True

        except SQLAlchemyError as e:
            session.rollback()
            session.close()
            print(f"Error deleting tag: {e}")
            return False


# Global instance for use in main.py
project_db = ProjectDB(DATABASE_URL)
