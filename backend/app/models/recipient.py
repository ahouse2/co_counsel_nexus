from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base

class Recipient(Base):
    __tablename__ = "recipients"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String)
