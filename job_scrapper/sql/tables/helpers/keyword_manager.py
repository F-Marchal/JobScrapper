from sqlalchemy.orm import Session, Query
from typing import Iterator

from job_scrapper.tools.secondary_logger_user import SecondaryLoggerUser
from logging import Logger
from job_scrapper.sql.tables.keywords.keyword_regex import KeywordRegex
from job_scrapper.sql.tables.keywords.keyword_version import KeywordVersion
from job_scrapper.sql.tables.keywords.selected_keyword_version import SelectedKeywordVersion
from sqlalchemy import and_
import re

class KeywordManager(SecondaryLoggerUser):
    def __init__(self, logger: Logger | None = None):
        super().__init__(logger)
        self._keywords = {}

    @property
    def keywords(self) -> dict[str, set[str]]:
        return {key: set_.copy() for key, set_ in self._keywords.items()}

    def regexes(self, keyword: str) -> set[str]:
        return self._keywords[keyword].copy()

    def versions(self, session: Session) -> dict[str, KeywordVersion]:
        return {
            keyword: self.get_keyword_version(session=session, keyword=keyword) for keyword in self._keywords.keys()
        }

    @property
    def keyword_patterns(self) -> dict[str, re.Pattern[str]]:
        result = {}
        for keyword, patterns in self.keywords.items():
            # Merge all pattern and ensure the largest pattern are at
            # the beginning of the list
            result[keyword] = re.compile("|".join(sorted(patterns, key=len, reverse=True)))
        return result

    @staticmethod
    def get_keywords_in_database(session: Session) -> list[str]:
        """Returns all versioned keywords contained in the database"""
        query = session.query(KeywordVersion.keyword).distinct()
        return [col for (col, *_) in query.all()]

    @staticmethod
    def get_latest_version(session: Session, keyword: str) -> KeywordVersion | None:
        """Returns the latest version of the keyword from the database"""
        return KeywordVersion.get_newest_version(session, keyword=keyword)
    
    @staticmethod
    def get_existing_keyword_versions(session: Session, keyword: str | None = None) -> dict[tuple[str, int], set[str]]:
        return KeywordVersion.summarise_versions(session, keyword=keyword)

    @classmethod
    def existing_version(cls, session: Session, keyword: str, regexes: set[str]) -> tuple[str, int] | None:
        """Say if a keyword version exists in the database. A version exist
        if it has the same set of regexes."""
        existing_version = cls.get_existing_keyword_versions(session, keyword=keyword)

        final_version: tuple[str, int] | None = None
        for version, version_regex in existing_version.items():
            if version_regex == regexes:
                final_version = version
                break
        
        return final_version

    def add_regex(self, keyword: str, regex: str, strict: bool=True) -> None:
        """Add a new regex to a keyword. Do not forget to use self.commit() to
        commit changes to database."""
        try:
            re.compile(regex)
        except re.error as e:
            if strict:
                raise re.error(f"Invalid regex for '{keyword}' : '{regex}'.\nError: {e}")
            else:
                self.logger.warning(
                    "Ignoring regex for '%s' : %s.\n"
                    "Error: %s",
                    keyword, regex, e
                )

        if keyword not in self._keywords:
            self._keywords[keyword] = set()

        self._keywords[keyword].add(regex)

    def remove_regex(self, keyword: str, regex: str) -> None:
        """Remove a regex from a keyword. Do not forget to use self.commit() to commit changes to database."""
        if keyword not in self._keywords:
            return
        self._keywords[keyword].remove(regex)

    def load(self, session: Session, keyword_version: KeywordVersion | str) -> None:
        if isinstance(keyword_version, str):
            keyword_version = self.get_existing_keyword_versions(session=session, keyword=keyword_version)

        regex = self.find_regexes(session=session, keyword=keyword_version)
        key =  keyword_version.keyword
        if key not in self._keywords:
            self._keywords[key] = regex
        else:
            self._keywords[key].clear()
            self._keywords[key] |= regex

    def load_all(self, session: Session):
        for keyword in self.find_all_keywords(session):
            version = self.get_latest_version(session=session, keyword=keyword)
            self.load(session=session, keyword_version=version)

    @classmethod
    def find_all_keywords(cls, session: Session) -> Iterator[str]:
        for k in session.query(KeywordVersion.keyword).distinct():
            yield k[0]

    @classmethod
    def find_all_versions(cls, session: Session) -> Query[KeywordVersion]:
        return session.query(KeywordVersion)


    @staticmethod
    def find_regexes(session: Session, keyword: KeywordVersion) -> set[str]:
        """Returns a set of regex associated to a keyword version."""
        regex_entry = session.query(KeywordRegex).join(
            KeywordVersion
        ).filter(
            and_(
                KeywordRegex.keyword == keyword.keyword,
                KeywordRegex.version == keyword.version
            )
        ).all()

        return {reg.regex for reg in regex_entry}

    def get_keyword_version(self, session: Session, keyword: str) -> KeywordVersion:
        version_tup = self.existing_version(session=session, keyword=keyword, regexes=self.regexes(keyword))

        if version_tup is not None:
            return KeywordVersion(keyword=keyword, version=version_tup[1])

        latest = self.get_latest_version(session=session, keyword=keyword)
        if latest is None:
            new_ver = 1
        else:
            new_ver = max(latest.version + 1, 1)  # Avoid version=0 when latest.version < 0

        return KeywordVersion(keyword=keyword, version=new_ver)

    def commit(self, session: Session) -> dict[str, KeywordVersion]:
        """Commit regex modification to database. A new Version will be added to database when needed."""
        result = {}
        for keywords, regexes in self._keywords.items():
            new_ver_entry = self.get_keyword_version(session=session, keyword=keywords)
            result[keywords] = new_ver_entry

            regexes = [
                KeywordRegex(
                    keyword=new_ver_entry.keyword,
                    version=new_ver_entry.version,
                    regex=reg,
                ) for reg in regexes
            ]

            session.add(new_ver_entry)
            session.add_all(regexes)
        return result

    @classmethod
    def set_selected_keyword_version(cls, session: Session, keyword: str, version: int):
        if not KeywordVersion(keyword=keyword, version=version).exists(session):
            raise KeyError(
                "Can not select keyword={keyword} and version={version}. Since this couple"
                "does not exist in the database."
            )
        session.add(
            SelectedKeywordVersion(keyword=keyword, version=version)
        )

    @classmethod
    def delete_selected_keyword_version(cls, session: Session, keyword: str) -> bool:
        """
        Remove the SelectedKeywordVersion attached to `keyword` from the database
        TO BE FOUND, SelectedKeywordVersion REQUIRE THAT THE SESSION HAS BEEN COMMITTED.
        """
        entry = cls.retrieve_selected_keyword_version(session, keyword=keyword)

        if not entry:
            return False

        session.delete(entry)
        return True

    @classmethod
    def retrieve_selected_keyword_version(cls, session: Session, keyword: str) -> SelectedKeywordVersion | None:
        """
        Retrieves the selected keyword version if it exists.
        TO BE FOUND, SelectedKeywordVersion REQUIRE THAT THE SESSION HAS BEEN COMMITTED.
        :param session: Session
        :param keyword: The requested keyword.
        :return: None if there is no SelectedKeywordVersion attached to this keyword, the version otherwise.
        """
        entry = session.query(
            SelectedKeywordVersion
        ).where(
            SelectedKeywordVersion.keyword == keyword
        ).first()

        if not entry:
            return None

        return entry

    @classmethod
    def retrieve_all_selected_keywords(cls, session: Session) -> Query[SelectedKeywordVersion]:
        """
        Retrieves all SelectedKeywordVersion entries from the database.
        TO BE FOUND, SelectedKeywordVersion REQUIRE THAT THE SESSION HAS BEEN COMMITTED.
        :param session: Session
        """
        return session.query(SelectedKeywordVersion)

    def load_all_selected_keywords(self, session: Session):
        """Load all keywords regexes that have a SelectedKeywordVersion in the database inside this manager.
         TO BE FOUND, SelectedKeywordVersion REQUIRE THAT THE SESSION HAS BEEN COMMITTED."""
        for entry in self.retrieve_all_selected_keywords(session=session):
            self.load(session=session, keyword_version=entry.version_entry)

    @classmethod
    def is_selected(cls, session: Session, version: KeywordVersion) -> bool:
        """Says if a KeywordVersion is selected.
         TO BE FOUND, SelectedKeywordVersion REQUIRE THAT THE SESSION HAS BEEN COMMITTED."""
        entry = session.query(SelectedKeywordVersion).where(
            and_(
                SelectedKeywordVersion.keyword == version.keyword,
                SelectedKeywordVersion.version == version.version,
            )
        ).first()
        return entry is not None

