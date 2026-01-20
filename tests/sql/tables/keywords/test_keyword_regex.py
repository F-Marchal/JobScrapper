import os.path

import pytest

from job_scrapper.sql.tables.keywords.keyword_version import KeywordVersion
from job_scrapper.sql.tables.keywords.keyword_regex import KeywordRegex
from tests.conftest import BaseTest
from sqlalchemy.exc import IntegrityError

@pytest.mark.js_tables
class TestKeywordRegex(BaseTest):
    """
    Ensure that Jobs table works as expected.

    Relationship test with JobExtraBase are exported to each JobExtraBase
    """

    def test_foreign_key(self):
        """Ensure foreign keys works as expected"""
        db = os.path.join(self.test_folder, "db1.db")
        ver1 = KeywordVersion(
            keyword="Alpha",
            version=1,
        )
        kr1 = KeywordRegex(
            keyword = "Alpha",
            version = 1,
            regex = ".*A.*"
        )
        kr2 = KeywordRegex(
            keyword = "Alpha",
            version = 1,
            regex = "alphabet"
        )
        kr3 = KeywordRegex(
            keyword = "Beta",
            version = 14,
            regex = ".*B.*"
        )
        self.screen_var("kr3", kr3)

        # Standard adding
        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            session.add(ver1)
            session.add(kr1)
            session.add(kr2)

        # Add a KeywordRegex without any KeywordVersion
        with pytest.raises(IntegrityError):
            with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
                    session.add(kr3)

    def test_relationship__version_entry(self):
        """Test KeywordRegex.version_entry"""
        # == Build default database ==
        db = os.path.join(self.test_folder, "db1.db")
        ver1 = KeywordVersion(
            keyword="Alpha",
            version=1,
        )
        kr1 = KeywordRegex(
            keyword = "Alpha",
            version = 1,
            regex = ".*A.*"
        )
        kr2 = KeywordRegex(
            keyword = "Alpha",
            version = 1,
            regex = "alphabet"
        )
        ver1_bis = ver1.copy()
        kr1_bis = kr1.copy()
        kr2_bis = kr2.copy()
        self.screen_var("ver1_bis", ver1_bis)
        self.screen_var("kr1_bis", kr1_bis)
        self.screen_var("kr2_bis", kr2_bis)

        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            session.add(ver1)
            session.add(kr1)
            session.add(kr2)
        # == Build default database ==

        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            # Extract kr1 from database and log .version_entry
            kr1_bis_from_db = kr1_bis.get_existing_self(session)
            self.screen_var("kr1_bis_from_db", kr1_bis_from_db)
            self.screen_multiple_vars("kr1_bis_from_db.version_entry", kr1_bis_from_db.version_entry)

            # Extract kr2 from database and log .version_entry
            kr2_bis_from_db = kr2_bis.get_existing_self(session)
            self.screen_var("kr2_bis_from_db", kr2_bis_from_db)
            self.screen_multiple_vars("kr2_bis_from_db.version_entry", kr2_bis_from_db.version_entry)

            # Ensure that we didn't get twice the same entry.
            assert kr2_bis_from_db != kr1_bis_from_db

            for kr_entry_from_database in [kr1_bis_from_db, kr2_bis_from_db]:
                assert kr_entry_from_database.version_entry == ver1_bis

    def test_deleted_with_version(self):
        db = os.path.join(self.test_folder, "db1.db")
        ver1 = KeywordVersion(
            keyword="Alpha",
            version=1,
        )

        self.screen_multiple_vars("ver{count}", ver1)

        kw1 = KeywordRegex(
            keyword="Alpha",
            version=1,
            regex="A"

        )
        self.screen_var("kw1", kw1)

        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            session.add_all([ver1, kw1])
            session.add(kw1)

        # Delete version element
        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            session.query(KeywordVersion).delete()

        # The Only keyword should have been deleted
        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            assert len(session.query(KeywordRegex).all()) == 0