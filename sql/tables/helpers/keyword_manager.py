from tools.secondary_logger_user import SecondaryLoggerUser
from logging import Logger
from sql.tables.keywords.keyword_version import KeywordVersion
from sql.tables.keywords.keyword_regex import KeywordRegex
from sql.tables.keywords.keyword_version import KeywordVersion


class KeywordManager(SecondaryLoggerUser):
    def __init__(self, logger: Logger | None):
        super().__init__(logger)

    def get_keywords_in_database(self):
