"""
This file contain a class that should be inherited by others in order to standardize log format
"""

import logging
import time
from contextlib import contextmanager
from typing import Generator


@contextmanager
def redirect_logs_to_file(logger, file) -> Generator:
    """Redirect log into a file"""

    file_handler = logging.StreamHandler(file)
    file_handler.setLevel(logger.level)
    file_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    logger.addHandler(file_handler)
    try:
        yield  # Allow user to take back control
    finally:
        # Supress the handler
        logger.removeHandler(file_handler)


RESET = "\033[0m"
COLORS = {
    logging.DEBUG: "\033[38;5;67m",  # "\033[94m",
    logging.INFO: "\033[92m",
    logging.WARNING: "\033[93m",
    logging.ERROR: "\033[91m",
    logging.CRITICAL: "\033[95m",
}


class _ColorFormatter(logging.Formatter):
    """
    Class used to format logger output.
    """

    def format(self, record):
        log_color = COLORS.get(record.levelno, RESET)
        message = super().format(record)
        local_time = time.localtime()
        formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
        return f"{log_color}[{formatted_time}] {message}{RESET}"


class CoreLogger:
    """
    Class that contain a formatted <logger>. This class is inherited
    by other in order to standardize log format.
    """

    # Class-level logger
    logger = logging.getLogger("CoreLogger")
    logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)

    formatter = _ColorFormatter("[%(levelname)s] %(message)s")
    stream_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.propagate = (
        False  # Prevent double logging if root logger also configured
    )
    logger_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    @classmethod
    def set_logging_level(cls, level: str):
        """
        Change logging level.
        :param str level: see cls.logger_levels
        :return:
        """
        level = level.upper()
        if level not in cls.logger_levels:
            raise ValueError(
                f"Logging level should be one of the following : {list(cls.logger_levels)}"
            )
        cls.logger.setLevel(cls.logger_levels[level])


if "__main__" == __name__:
    CL = CoreLogger()
    CL.logger.info("Yey !")

    with open(".tmp.tmp", "w", encoding="utf-8") as tmp_file:
        with redirect_logs_to_file(CL.logger, tmp_file):
            CL.logger.info("Alpha !")
            CL.logger.info("Beta !")
        CL.logger.info("Fin !")
