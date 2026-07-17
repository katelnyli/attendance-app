from sqlalchemy import Column, String, Integer, Text
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.associations import role_permissions

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    resource = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    description = Column(Text)

    # relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
