from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from backend.app.database import Base
from backend.app.models.user_role import user_role_association
from backend.app.models.role_permission import role_permission_association
from backend.app.models.sql import User

class Role(Base):
    __tablename__ = "roles"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    users = relationship(User, secondary=user_role_association, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permission_association, back_populates="roles")
