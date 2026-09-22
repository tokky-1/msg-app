import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from repository.health_repo import HealthRepository

logger = logging.getLogger(__name__)

class HealthService:
    def __init__(self, db: Session):
        self.repo = HealthRepository(db)

    def is_db_ready(self) -> bool:
        try:
            self.repo.ping()
            return True
        except SQLAlchemyError as exc:
            logger.error("Database readiness check failed", extra={"error": str(getattr(exc, "orig", None) or exc).strip()})
            return False
