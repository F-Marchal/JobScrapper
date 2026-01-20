from sqlalchemy import Column, String, Integer, ForeignKeyConstraint
from sqlalchemy.orm import relationship, validates
from job_scrapper.sql.tables.base_table import BaseTable
import re

class KeywordRegex(BaseTable):
    """Should contain regexes associated to a keyword version.

    At this time, those regexes can be added or removed without
    requiring any modification of KeywordVersion."""
    __abstract__ = False
    __tablename__ = "keyword_regex"

    keyword = Column(String, nullable=False, primary_key=True)
    version = Column(Integer, nullable=False, primary_key=True)
    regex = Column(String, primary_key=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["keyword", "version"],
            ["keyword_version.keyword", "keyword_version.version"],
            ondelete="CASCADE",
        ),
    )

    version_entry = relationship(
        "KeywordVersion",
        back_populates="regex_entries",
        passive_deletes=True,
    )

    @validates("regex")
    def validate_regex(self, key, value):
        try:
            re.compile(value)
        except re.error as e:
            raise ValueError(f"Invalid regex '{value}': {e}")
        return value

