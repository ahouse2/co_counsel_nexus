from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from backend.app.database import Base
from backend.app.models.role_permission import role_permission_association

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    roles = relationship("Role", secondary=role_permission_association, back_populates="permissions")
