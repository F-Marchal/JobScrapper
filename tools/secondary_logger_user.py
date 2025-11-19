from tools.logger_core import CoreLogger, logging

class SecondaryLoggerUser:
    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger if logger is not None else CoreLogger.logger


