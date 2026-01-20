from sqlalchemy import Column, String, Integer, Boolean, ForeignKeyConstraint
from sqlalchemy.orm import relationship, Session, Query

from job_scrapper.sql.tables.base_table import BaseTable


class SelectedKeywordVersion(BaseTable):
    __abstract__ = False
    __tablename__ = 'keyword_selected_version'

    keyword = Column(String, primary_key=True)
    version = Column(Integer)

    __table_args__ = (
        ForeignKeyConstraint(
            ["keyword", "version"],
            ["keyword_version.keyword", "keyword_version.version"],
        ondelete="CASCADE",
        ),

    )
    version_entry = relationship(
        "KeywordVersion",
        back_populates="selected_entry",
        passive_deletes=True,
    )


