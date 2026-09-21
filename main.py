from fastapi import FastAPI
from core.config import settings
from core.log_config import setup_logging

setup_logging(settings.LOG_LEVEL)
app = FastAPI(title="MSG",
    description= "typically messaging platform but built by me ",
    version="1.0.0",
    contact={"name":"Ayo-Ajayi Oluwatokiloba","email":"tokkyayoajayi@gmail.com"},)