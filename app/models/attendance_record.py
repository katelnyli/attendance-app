from sqlalchemy import DateTime, Column, String, func, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    file_id = Column(UUID(as_uuid=True), ForeignKey("uploaded_files.id"), nullable=False)
    user_name = Column(String(255), nullable=False, index=True)
    hours_worked = Column(Float, nullable=False)
    date = Column(DateTime(timezone=True), nullable=False, index=True)

    uploaded_file = relationship("UploadedFile", back_populates="attendance_records")
    