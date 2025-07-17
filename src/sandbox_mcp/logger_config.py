"""日志配置模块，将日志输出到文件和控制台。"""


def setup_logger():
    """初始化日志系统，分级别写入不同文件，并输出到控制台。"""
    import logging
    import os
    from logging.handlers import RotatingFileHandler

    LOG_DIR = os.path.join(os.path.dirname(__file__), '../../logs')
    os.makedirs(LOG_DIR, exist_ok=True)

    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"

    INFO_LOG = os.path.join(LOG_DIR, 'info.log')
    ERROR_LOG = os.path.join(LOG_DIR, 'error.log')
    WARN_LOG = os.path.join(LOG_DIR, 'warn.log')
    SYS_LOG = os.path.join(LOG_DIR, 'sys.log')

    info_handler = RotatingFileHandler(INFO_LOG, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    info_handler.addFilter(lambda record: record.levelno == logging.INFO)

    error_handler = RotatingFileHandler(ERROR_LOG, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    error_handler.addFilter(lambda record: record.levelno == logging.ERROR)

    warn_handler = RotatingFileHandler(WARN_LOG, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    warn_handler.setLevel(logging.WARNING)
    warn_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    warn_handler.addFilter(lambda record: record.levelno == logging.WARNING)

    sys_handler = RotatingFileHandler(SYS_LOG, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
    sys_handler.setLevel(logging.DEBUG)
    sys_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    logging.basicConfig(
        level=logging.DEBUG,
        format=LOG_FORMAT,
        handlers=[info_handler, error_handler, warn_handler, sys_handler, console_handler]
    )
