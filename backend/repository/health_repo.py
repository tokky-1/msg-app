from sqlalchemy import text
from sqlalchemy.orm import Session

class HealthRepository:
    def __init__(self, db: Session):
        self.db = db

    def ping(self) -> None:
        """Run a trivial query; raises SQLAlchemyError if the DB is unreachable."""
        self.db.execute(text("SELECT 1"))
