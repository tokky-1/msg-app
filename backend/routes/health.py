from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from db.connect import get_db
from services.health_service import HealthService

router = APIRouter(tags=["health"])

@router.get("/health")
def health():
    """Liveness: the process is up. Never touches the DB."""
    return {"status": "ok"}

@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    """Readiness: the app can reach the DB."""
    if HealthService(db).is_db_ready():
        return {"status": "ok"}
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "unavailable"},
    )
