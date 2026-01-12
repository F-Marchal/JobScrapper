import pytest

from job_scrapper.sql.tables.keywords.keyword_version import KeywordVersion
from job_scrapper.sql.tables.keywords.keyword_regex import KeywordRegex
from tests.conftest import BaseTest
import os

@pytest.mark.js_tables
class TestKeywordVersion(BaseTest):
    def test_relationship__regex_entries(self):
        """Test KeywordVersion.regex_entries"""
        db = os.path.join(self.test_folder, "db1.db")
        ver1 = KeywordVersion(
            keyword="Alpha",
            version=1,
        )
        kr1 = KeywordRegex(
            keyword="Alpha",
            version=1,
            regex=".*A.*"
        )
        kr2 = KeywordRegex(
            keyword="Alpha",
            version=1,
            regex="alphabet"
        )
        self.screen_var("miniVer1", ver1)
        self.screen_var("miniKr1", kr1)
        self.screen_var("miniKr2", kr2)

        ver1_bis = ver1.copy()
        kr1_bis = kr1.copy()
        kr2_bis = kr2.copy()
        self.screen_var("ver1_bis", ver1_bis)
        self.screen_var("kr1_bis", kr1_bis)
        self.screen_var("kr2_bis", kr2_bis)

        with KeywordVersion.get_session(db, logger=self.icl.logger) as session:
            session.add(ver1)
            session.add(kr1)
            session.add(kr2)


        with KeywordVersion.get_session(db, logger=self.icl.logger) as session:
            ver1_from_db = ver1_bis.get_existing_self(session)
            self.screen_var("ver1_from_db", ver1_from_db)
            self.screen_multiple_vars("ver1_from_db.regex_entries_", *ver1_from_db.regex_entries)

            assert len(ver1_from_db.regex_entries) == 2
            assert kr1_bis in ver1_from_db.regex_entries
            assert kr2_bis in ver1_from_db.regex_entries

    def test_relationship__available_version_entries(self):
        # == Build default database ==
        db = os.path.join(self.test_folder, "db1.db")
        ver1 = KeywordVersion(
            keyword="Alpha",
            version=1,
        )
        ver2 = KeywordVersion(
            keyword="Alpha",
            version=2,
        )
        ver3 = KeywordVersion(
            keyword="Beta",
            version=1,
        )
        kr1 = KeywordRegex(
            keyword = "Alpha",
            version = 1,
            regex = ".*A.*"
        )
        self.screen_multiple_vars("ver{count}", ver1, ver2, ver3)
        self.screen_var("kr1", kr1)
        ver1_bis = ver1.copy()
        ver2_bis = ver2.copy()
        ver3_bis = ver3.copy()
        kr1_bis = kr1.copy()
        self.screen_multiple_vars("ver{count}_bis", ver1_bis, ver2_bis, ver3_bis)
        self.screen_var("kr1_bis", kr1_bis)

        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            session.add_all([ver1, ver2, ver3])
            session.add(kr1)
         # == Build default database ==

        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            all_version = KeywordVersion.get_available_versions(session, keyword=kr1_bis.keyword).all()
            self.screen_multiple_vars("Version", *all_version)

            # Does all_version contains the correct set of version entry
            assert ver1_bis in all_version
            assert ver2_bis in all_version
            assert ver3_bis not in all_version

            # Do we find the correct newest version ?
            newest_ver = KeywordVersion.get_newest_version(session, keyword=kr1_bis.keyword)
            self.screen_var("Newest", newest_ver)
            assert newest_ver.keyword == kr1_bis.keyword
            assert newest_ver == ver2_bis

    def test_get_newest_version_empty_db(self):
        db = os.path.join(self.test_folder, "db1.db")
        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            assert KeywordVersion.get_newest_version(session, keyword="NOTHING") is None


    def test_summarise_versions(self):
        db = os.path.join(self.test_folder, "db1.db")
        ver1 = KeywordVersion(
            keyword="Alpha",
            version=1,
        )
        ver2 = KeywordVersion(
            keyword="Alpha",
            version=2,
        )
        ver3 = KeywordVersion(
            keyword="Beta",
            version=1,
        )
        self.screen_multiple_vars("ver", ver1, ver2, ver3)

        regex1 = KeywordRegex(keyword="Alpha", version=1, regex=".*A.*")
        regex2 = KeywordRegex(keyword="Alpha", version=1, regex=".*Alpha.*")
        regex3 = KeywordRegex(keyword="Alpha", version=2, regex="Hello")
        regex4 = KeywordRegex(keyword="Beta", version=1, regex=".*Beta.*")
        self.screen_multiple_vars("regex", regex1, regex2, regex3, regex4)

        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            session.add_all([ver1, ver2, ver3, regex1, regex2, regex3, regex4])

        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            summary = KeywordVersion.summarise_versions(session)
            expected = {('Alpha', 1): {'.*Alpha.*', '.*A.*'}, ('Alpha', 2): {'Hello'}, ('Beta', 1): {'.*Beta.*'}}

            self.screen_var("summary", summary)
            self.screen_var("expected", expected)

            assert summary == expected

        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            summary = KeywordVersion.summarise_versions(session, keyword='Alpha')
            expected = {('Alpha', 1): {'.*Alpha.*', '.*A.*'}, ('Alpha', 2): {'Hello'}}

            self.screen_var("summary", summary)
            self.screen_var("expected", expected)

            assert summary == expected

        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            summary = KeywordVersion.summarise_versions(session, keyword='Beta')
            expected = {('Beta', 1): {'.*Beta.*'}}

            self.screen_var("summary", summary)
            self.screen_var("expected", expected)

            assert summary == expected
