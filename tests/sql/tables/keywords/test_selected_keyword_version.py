import os.path

import pytest

from job_scrapper.sql.tables.keywords.keyword_version import KeywordVersion
from job_scrapper.sql.tables.keywords.selected_keyword_version import SelectedKeywordVersion
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
        kr1 = SelectedKeywordVersion(
            keyword = "Alpha",
            version = 1,
        )
        kr2 = SelectedKeywordVersion(
            keyword = "Alpha",
            version = 1,
        )
        kr3 = SelectedKeywordVersion(
            keyword = "Beta",
            version = 14,
        )
        self.screen_var("kr3", kr3)

        # Standard adding
        with SelectedKeywordVersion.get_session(db, logger=self.icl.logger) as session:
            session.add(ver1)
            session.add(kr1)
            session.add(kr2)

        # Add a KeywordRegex without any KeywordVersion
        with pytest.raises(IntegrityError):
            with SelectedKeywordVersion.get_session(db, logger=self.icl.logger) as session:
                    session.add(kr3)

    def test_deleted_with_version(self):
        db = os.path.join(self.test_folder, "db1.db")
        ver1 = KeywordVersion(
            keyword="Alpha",
            version=1,
        )

        self.screen_multiple_vars("ver{count}", ver1)

        kw1 = SelectedKeywordVersion(
            keyword="Alpha",
            version=1,

        )
        self.screen_var("kw1", kw1)

        with SelectedKeywordVersion.get_session(db, logger=self.icl.logger) as session:
            session.add_all([ver1, kw1])
            session.add(kw1)

        # Delete version element
        with SelectedKeywordVersion.get_session(db, logger=self.icl.logger) as session:
            session.query(KeywordVersion).delete()

        # The Only keyword should have been deleted
        with SelectedKeywordVersion.get_session(db, logger=self.icl.logger) as session:
            assert len(session.query(SelectedKeywordVersion).all()) == 0