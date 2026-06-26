import sys
import os
import json
import contextvars
from loguru import logger

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_dir = os.path.join(root_dir, "logs")
if not os.path.exists(log_dir):
    os.mkdir(log_dir)

# Context variable carrying the current request ID (set by RequestTracingMiddleware)
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


def _json_sink(message):
    record = message.record
    payload = {
        "time": record["time"].isoformat(),
        "level": record["level"].name,
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
        "request_id": request_id_var.get("-"),
        "message": record["message"],
    }
    print(json.dumps(payload, ensure_ascii=False), file=sys.stdout, flush=True)


class MyLogger:
    def __init__(self):
        self.logger = logger
        self.logger.remove()

        try:
            from core.config import get_settings
            log_format = get_settings().log_format
        except Exception:
            log_format = "text"

        if log_format == "json":
            self.logger.add(_json_sink, level="DEBUG")
        else:
            self.logger.add(
                sys.stdout,
                level="DEBUG",
                format=(
                    "<green>{time:YYYYMMDD HH:mm:ss}</green> | "
                    "{process.name} | "
                    "{thread.name} | "
                    "<cyan>{module}</cyan>.<cyan>{function}</cyan>"
                    ":<cyan>{line}</cyan> | "
                    "<level>{level}</level>: "
                    "<level>{message}</level>"
                ),
            )

    def get_logger(self):
        return self.logger


log = MyLogger().get_logger()
