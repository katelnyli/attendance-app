from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.associations import user_roles

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    email = Column(String(225), unique=True, nullable=False, index=True) # index speeds up login queries
    full_name = Column(String(225), nullable=False)
    hashed_password = Column(String(225), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    roles = relationship("Role", secondary=user_roles, back_populates="users")
    uploaded_files = relationship("UploadedFile", back_populates="uploader")
