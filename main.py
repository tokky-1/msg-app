from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from core.config import settings
from core.errors import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    RuleViolationError,
)
from core.log_config import setup_logging
from routes import health ,auth

setup_logging(settings.LOG_LEVEL)
app = FastAPI(title="MSG",
    description= "typically messaging platform but built by me ",
    version="1.0.0",
    contact={"name":"Ayo-Ajayi Oluwatokiloba","email":"tokkyayoajayi@gmail.com"},)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Map each domain error category to an HTTP status code.
DOMAIN_ERROR_STATUS = {
    NotFoundError: 404,
    PermissionDeniedError: 403,
    RuleViolationError: 400,
    ConflictError: 409,
    RateLimitError: 429,
}

def make_domain_error_handler(status_code: int):
    async def handler(request: Request, exc: DomainError):
        return JSONResponse(status_code=status_code, content={"detail": exc.message})
    return handler

for error_cls, status_code in DOMAIN_ERROR_STATUS.items():
    app.add_exception_handler(error_cls, make_domain_error_handler(status_code))

app.include_router(health.router)
app.include_router(auth.authrouter)