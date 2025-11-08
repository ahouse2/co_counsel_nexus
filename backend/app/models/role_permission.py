from sqlalchemy import Table, Column, String, ForeignKey
from backend.app.database import Base

role_permission_association = Table(
    "role_permission_association",
    Base.metadata,
    Column("role_id", String, ForeignKey("roles.id")),
    Column("permission_id", String, ForeignKey("permissions.id")),
)
