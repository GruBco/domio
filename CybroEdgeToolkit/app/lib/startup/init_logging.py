import logging
import logging.handlers
import os
import sys
from pathlib import Path
from lib.config.config.debuglog_config import DebugLogConfig

# copy log messages also to stdout
LOG_TO_STD_OUT = True


def init_logging(log_config: DebugLogConfig,
                 log_dir: Path,
                 filename: str) -> None:
    """Initialize the logging module.

    :param log_config: The config object.
    :param log_dir: The log directory.
    :param filename: The filename without extension (it is appended .log) in
    which to store logs.
    """
    handlers = []

    if log_config.enabled:
        if log_config.log_to_file:
            handlers.append(
                _create_file_handler(
                    log_config.verbose_level,
                    log_dir,
                    filename,
                    log_config.max_log_file_size_kb,
                    log_config.max_log_backup_count
                )
            )

        if LOG_TO_STD_OUT:
            handlers.append(logging.StreamHandler(sys.stdout))

        logging.basicConfig(
            level=log_config.verbose_level,
            format="%(asctime)s |"
                   " %(threadName)-10.10s |"
                   " %(levelname)-5.5s |"
                   " %(name)-18.18s |"
                   " %(message)s",
            datefmt="%m.%d.%Y %H:%M:%S",
            handlers=handlers
        )


def _create_file_handler(level: str,
                         log_dir: Path,
                         filename: str,
                         max_size_kb: int,
                         backup_count: int):
    file = log_dir.joinpath(f"{filename}.log")

    if not os.path.isdir(log_dir):
        os.makedirs(log_dir, mode=0o755, exist_ok=False)

    result = logging.handlers.RotatingFileHandler(
        str(file),
        maxBytes=max_size_kb * 1000,
        backupCount=backup_count
    )
    result.setLevel(level)
    return result
