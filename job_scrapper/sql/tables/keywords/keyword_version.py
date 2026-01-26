
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship, Session, Query

from job_scrapper.sql.tables.base_table import BaseTable

class KeywordVersion(BaseTable):
    __abstract__ = False
    __tablename__ = "keyword_version"

    keyword = Column(String, primary_key=True)
    version = Column(Integer, primary_key=True)

    regex_entries = relationship(
        "KeywordRegex",
        back_populates="version_entry",
        cascade="all, delete-orphan",
    )

    keyword_entries = relationship(
        "Keywords",
        back_populates="version_entry",
        cascade="all, delete-orphan",
    )

    selected_entry = relationship(
        "SelectedKeywordVersion",
        back_populates="version_entry",
        cascade="all, delete-orphan",
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

    @classmethod
    def summarise_versions(cls, session: Session, keyword: str | None=None) -> dict[tuple[str, int], set[str]]:
        """Summarize versions object for a certain keyword (keyword='keyword') if for all keywords.
        Returns a dictionary (keyword, version): set of regexes attached to this keyword version."""
        if not keyword:
            query = session.query(KeywordVersion)

        else:
            query = session.query(KeywordVersion).where(KeywordVersion.keyword == keyword)

        result: dict[tuple[str, int], set[str]] = {}

        for versions in query.all():
            key = str(versions.keyword), int(str(versions.version))
            regexes = {str(regex_entry.regex) for regex_entry in versions.regex_entries}
            result[key] = regexes

        return result
