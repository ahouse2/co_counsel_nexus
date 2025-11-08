from sqlalchemy import Table, Column, String, ForeignKey
from backend.app.database import Base

user_role_association = Table(
    "user_role_association",
    Base.metadata,
    Column("user_id", String, ForeignKey("users.id")),
    Column("role_id", String, ForeignKey("roles.id")),
)
