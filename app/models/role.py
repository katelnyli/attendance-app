from sqlalchemy import Column, String, Integer, Text
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.associations import user_roles, role_permissions

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)

    # relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")