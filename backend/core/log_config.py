import logging
import sys

from pythonjsonlogger.json import JsonFormatter


def setup_logging(level: str) -> None:
    # 1. Create a StreamHandler that writes to sys.stdout
    handler = logging.StreamHandler(sys.stdout)

    # 2. Give it a JsonFormatter
    handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    # 3. Get the root logger, remove any existing handlers, add your handler, set the level
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # 4. Route uvicorn's loggers through the root handler so everything is JSON
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True