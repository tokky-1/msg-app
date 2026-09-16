from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base 
from core.config import settings


DB_URL = settings.DB_URL
engine = create_engine(DB_URL, connect_args={"connect_timeout": 5}, echo=True)
SessionLocal = sessionmaker(bind = engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        