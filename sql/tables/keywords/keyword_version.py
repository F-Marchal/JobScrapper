
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship, Session, Query
from typing import Sequence

from sql.tables.base_table import BaseTable

class KeywordVersion(BaseTable):
    __abstract__ = False
    __tablename__ = "keyword_version"

    keyword = Column(String, primary_key=True)
    version = Column(Integer, primary_key=True)

    regex_entries = relationship(
        "KeywordRegex",
    )
    keyword_entries = relationship(
        "Keywords",
    )

    @classmethod
    def get_available_versions(cls, session: Session, keyword: str) -> Query:
        """Get all available version for a certain keyword (query object)"""
        return session.query(cls).filter_by(keyword=keyword)

    @classmethod
    def get_newest_version(cls, session: Session, keyword: str) -> 'KeywordVersion | None' :
        """Get the newest version for a certain keyword (query object)"""
        all_ver = cls.get_available_versions(session, keyword).all()
        if len(all_ver) == 0:
            return None
        return max(all_ver,  key=lambda x: x.version)


