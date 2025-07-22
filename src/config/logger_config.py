import logging
import os
import sys
from concurrent_log_handler import ConcurrentRotatingFileHandler
from config.config import settings
from contextvars import ContextVar

# Used to store request_id in contextvars
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="AI-SANDBOX")


# Custom Formatter to handle missing attributes
class RequestIDFormatter(logging.Formatter):
    def format(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = request_id_ctx_var.get()
        return super().format(record)


# Log filter to add request_id to records
class RequestIDLogFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_ctx_var.get()
        return True


def setup_logger():
    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create a formatter, add request_id to log format
    formatter = RequestIDFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s - %(filename)s:%(lineno)d"
    )

    # Check and create log directory
    log_dir = settings.log_dir
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Create a handler for sys.log
    sys_log_file_path = os.path.join(log_dir, "sys.log")
    sys_file_handler = ConcurrentRotatingFileHandler(
        sys_log_file_path,
        mode="a",
        maxBytes=5 * 1024 * 1024,
        backupCount=30,
        encoding="utf-8",
    )
    sys_file_handler.setLevel(logging.INFO)
    sys_file_handler.setFormatter(formatter)
    sys_file_handler.addFilter(RequestIDLogFilter())

    # Create a handler for info.log
    info_log_file_path = os.path.join(log_dir, "info.log")
    info_file_handler = ConcurrentRotatingFileHandler(
        info_log_file_path,
        mode="a",
        maxBytes=5 * 1024 * 1024,
        backupCount=30,
        encoding="utf-8",
    )
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.setFormatter(formatter)
    info_file_handler.addFilter(RequestIDLogFilter())
    info_file_handler.addFilter(lambda record: record.levelno == logging.INFO)

    # Create a handler for warn.log
    warn_log_file_path = os.path.join(log_dir, "warn.log")
    warn_file_handler = ConcurrentRotatingFileHandler(
        warn_log_file_path,
        mode="a",
        maxBytes=5 * 1024 * 1024,
        backupCount=30,
        encoding="utf-8",
    )
    warn_file_handler.setLevel(logging.WARNING)
    warn_file_handler.setFormatter(formatter)
    warn_file_handler.addFilter(RequestIDLogFilter())
    warn_file_handler.addFilter(lambda record: record.levelno == logging.WARNING)

    # Create a handler for error.log
    error_log_file_path = os.path.join(log_dir, "error.log")
    error_file_handler = ConcurrentRotatingFileHandler(
        error_log_file_path,
        mode="a",
        maxBytes=5 * 1024 * 1024,
        backupCount=30,
        encoding="utf-8",
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    error_file_handler.addFilter(RequestIDLogFilter())
    error_file_handler.addFilter(lambda record: record.levelno == logging.ERROR)

    # Create a console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIDLogFilter())

    # Clear existing handlers and add ours
    logger.handlers = [
        sys_file_handler,
        info_file_handler,
        warn_file_handler,
        error_file_handler,
        console_handler,
    ]
