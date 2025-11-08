from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from backend.app.database import Base
from backend.app.models.user_role import user_role_association

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    roles = relationship("Role", secondary=user_role_association, back_populates="users")
