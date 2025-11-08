
from __future__ import annotations
from typing import Any, Dict, List
import sqlalchemy
from sqlalchemy import text

from backend.app.config import get_settings

class DatabaseQueryService:
    """
    A service for executing queries against various databases.
    Currently supports SQL databases via SQLAlchemy.
    """

    def __init__(self):
        settings = get_settings()
        # Assuming a default SQL database URI is available in settings
        self.sql_database_uri = settings.sql_database_uri # Placeholder for a new setting
        self.engine = None

    async def _get_engine(self):
        if self.engine is None:
            if not self.sql_database_uri:
                raise ValueError("SQL Database URI is not configured in settings.")
            self.engine = sqlalchemy.create_engine(self.sql_database_uri)
        return self.engine

    async def execute_query(self, query: str, db_type: str = "sql") -> List[Dict[str, Any]]:
        """
        Executes a query against the specified database type.
        
        :param query: The query string to execute.
        :param db_type: The type of database (e.g., "sql").
        :return: A list of dictionaries, where each dictionary represents a row.
        """
        if db_type.lower() == "sql":
            engine = await self._get_engine()
            async with engine.connect() as connection:
                result = await connection.execute(text(query))
                rows = result.fetchall()
                columns = result.keys()
                return [dict(zip(columns, row)) for row in rows]
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

