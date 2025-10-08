"""
This file contain a class that should be inherited by others in order to standardize log format.
Add a context manager `redirect_logs_to_file` Redirect logs into a file.
Add a _ColorFormatter that format logger output.
Add a CoreLogger file that can be used
"""

import logging
import time
from contextlib import contextmanager
from typing import Generator


@contextmanager
def redirect_logs_to_file(logger, file, level: str | None | int = None) -> Generator:
    """
    Redirect log into a file
    :param logger: A logger
    :param file: An opened file in which logs will be written.
    :param level: The level of logging (Debug, Info ...)
    :return:
    """
    if level is None:
        level = logger.level

    file_log_handler = logging.StreamHandler(file)
    file_log_handler.setLevel(level)
    file_log_handler.setFormatter(
        logging.Formatter("[%(levelname)s] %(message)s")
    )

    logger.addHandler(file_log_handler)
    try:
        yield  # Allow user to take back control
    finally:
        # Supress the handler
        logger.removeHandler(file_log_handler)




class _ColorFormatter(logging.Formatter):
    """
    Class used to format logger output.
    """
    log_reset_color = "\033[0m"
    log_colors = {
        logging.DEBUG: "\033[38;5;67m",
        logging.INFO: "\033[92m",
        logging.WARNING: "\033[93m",
        logging.ERROR: "\033[91m",
        logging.CRITICAL: "\033[95m",
    }

    def format(self, record):
        log_color = self.log_colors.get(record.levelno, self.log_reset_color)
        message = super().format(record)
        local_time = time.localtime()
        formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
        return f"{log_color}[{formatted_time}] {message}{self.log_reset_color}"


class CoreLogger:
    """
    Class that contain a formatted <logger>. This class is inherited
    by other in order to standardize log format.
    """

    # Class-level logger
    logger = logging.getLogger("CoreLogger")
    logger.setLevel(logging.DEBUG)

    # Class-level stream handler
    # (Part that format logs)
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

    # Class-level file handler (Use start_file_logging / stop_file_logging)
    # to configure it
    file_log_handler = None
    log_file = None

    @classmethod
    def start_file_logging(cls, path: str, level: str | None | int = None) -> bool:
        """
        Redirect logs into a file.
        :param path: A path that lead to a file
        :param level: Level of logging see : cls.logger_levels
        :return bool: Do the function succeed ?
        """
        if not (cls.file_log_handler is None and cls.log_file is None):
            cls.logger.warning(
                "Can not start file logging. file_log_handler or log_file"
                " already exist :\nHandler : %s\nfile : %s",
                cls.file_log_handler,
                cls.log_file,
            )
            return False

        cls.log_file = open(path, "w", encoding="UTF-8")

        if level is None:
            level = cls.logger.level
        elif not isinstance(level, int):
            level = cls.logger_levels[level]

        cls.file_log_handler = logging.StreamHandler(cls.log_file)
        cls.file_log_handler.setLevel(level)

        cls.file_log_handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
        )

        cls.logger.addHandler(cls.file_log_handler)

        return True

    @classmethod
    def stop_file_logging(cls):
        """
        Stop log redirection into cls.log_file
        :return:
        """
        if cls.file_log_handler:
            cls.logger.removeHandler(cls.file_log_handler)
            cls.file_log_handler.close()
            cls.file_log_handler = None

        if cls.log_file:
            cls.log_file.close()
            cls.log_file = None

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
        cls.stream_handler.setLevel(cls.logger_levels[level])

    @classmethod
    @contextmanager
    def redirect_logs_to_file(cls, file, level: str | None = None) -> Generator:
        """
        Hijack class logger to redirect logs into a file. Logs still shows
        in terminal. Should be used with the `with` statement.
        For long term log redirection, please see `start_file_logging` and `stop_file_logging`.
        :param file: An opened file in which logs will be written.
        :param level: The level of logging (DEBUG, INFO ...)
        :return:
        """
        if level is None:
            level = list(cls.logger_levels)[0]

        with redirect_logs_to_file(cls.logger, file=file, level=cls.logger_levels[level]):
            yield


if "__main__" == __name__:
    CL = CoreLogger()
    CL.logger.info("Yey !")

    with open(".tmp.tmp", "w", encoding="utf-8") as tmp_file:
        with redirect_logs_to_file(CL.logger, tmp_file, level="INFO"):
            CL.logger.debug("Alpha !")
            CL.logger.info("Beta !")
        CL.logger.info("Fin !")
