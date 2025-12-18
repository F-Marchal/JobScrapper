import os

from tests.conftest import BaseTest
from sql.tables.helpers.keyword_manager import KeywordManager, KeywordVersion, KeywordRegex

class TestKeywordManager(BaseTest):
    def test_get_keywords_in_database(self):
        # Setup
        db = os.path.join(self.test_folder, "db1")
        kv1 = KeywordVersion(
            keyword="Alpha",
            version=1,
        )
        kv2 = KeywordVersion(
            keyword="Alpha",
            version=2,
        )
        kv3 = KeywordVersion(
            keyword="Beta",
            version=1,
        )
        self.screen_multiple_vars("kv", kv1, kv2, kv3)
        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            session.add_all([kv1, kv2, kv3])

        km = KeywordManager(logger=self.icl.logger)
        self.screen_var("km", km)

        # Test
        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            keywords = km.get_keywords_in_database(session)
            assert len(keywords) == 2
            assert list(keywords) == ["Alpha", "Beta"]

    def test_get_latest_version(self):
        # Setup
        db = os.path.join(self.test_folder, "db1")
        kv1 = KeywordVersion(
            keyword="Alpha",
            version=1,
        )
        kv2 = KeywordVersion(
            keyword="Alpha",
            version=2,
        )
        kv3 = KeywordVersion(
            keyword="Beta",
            version=1,
        )
        self.screen_multiple_vars("kv", kv1, kv2, kv3)
        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            session.add_all([kv1, kv2, kv3])

        km = KeywordManager(logger=self.icl.logger)
        self.screen_var("km", km)

        # Test
        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            alpha_ver = km.get_latest_version(session, "Alpha")
            beta_ver = km.get_latest_version(session, "Beta")

            assert alpha_ver.version == 2 and alpha_ver.keyword == "Alpha"
            assert beta_ver.version == 1 and beta_ver.keyword == "Beta"

    def test_get_keyword_versions(self):
        # Just a wrapper
        pass

    def test_existing_version(self):
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

        km = KeywordManager(logger=self.icl.logger)

        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            version1 = km.existing_version(session,"Alpha", {"Hello", })
            assert version1 == ("Alpha", 2)

            version2 = km.existing_version(session,"Alpha", {".*A.*", ".*Alpha.*"})
            assert version2 == ("Alpha", 1)

            version3 = km.existing_version(session,"Alpha", {".*Beta.*", })
            assert version3 is None

    def test_load(self):
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

        km = KeywordManager(logger=self.icl.logger)
        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            km.load_all(session)

        assert km.keywords == {
            "Alpha": {"Hello", },
            "Beta": {".*Beta.*"}
        }

        # Load an older version
        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            km.load(session, keyword_version=KeywordVersion(keyword="Alpha", version=1))

        assert km.keywords == {
            "Alpha": {".*A.*", ".*Alpha.*"},
            "Beta": {".*Beta.*"}
        }

    def test_add_remove_commit_regex(self):
        db = os.path.join(self.test_folder, "db1.db")
        km = KeywordManager(logger=self.icl.logger)
        self.screen_var("km", km)
        km.add_regex("Alpha", ".*Alpha.*")
        km.add_regex("Alpha", ".*A.*")
        km.add_regex("Beta", ".*Beta.*")
        self.re_screen_var("km")

        self.tracker.write("Test empty db")
        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            # Database is empty
            assert len(session.query(KeywordVersion).all()) == 0

        self.tracker.write("Commit km")
        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            # Add newly added keyword to database
            km.commit(session)

        self.tracker.write("Request db")
        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            alpha_ver1_l = session.query(KeywordVersion).where(KeywordVersion.keyword == "Alpha").all()
            self.screen_var("alpha_ver_l", alpha_ver1_l)
            assert len(alpha_ver1_l) == 1
            alpha_ver1 = alpha_ver1_l[0]

            self.screen_var("alpha_ver", alpha_ver1)
            alpha_ver1_regexes = km.find_regexes(session, alpha_ver1)

            assert alpha_ver1_regexes == {".*Alpha.*", ".*A.*"}

        # Remove a regex to create a new  version
        km.remove_regex("Alpha", ".*Alpha.*")
        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            km.commit(session)

        with KeywordRegex.get_session(db, logger=self.icl.logger) as session:
            alpha_ver2_l = session.query(KeywordVersion).where(KeywordVersion.keyword == "Alpha").all()

            # A new version should exist
            assert len(alpha_ver2_l) == 2

            v2_alpha = km.get_latest_version(session, "Alpha")
            assert v2_alpha in alpha_ver2_l # Just to ensure everything went find

            self.screen_var("v2_alpha", v2_alpha)
            alpha_ver2_regexes = km.find_regexes(session, v2_alpha)

            assert alpha_ver2_regexes == {".*A.*"}

