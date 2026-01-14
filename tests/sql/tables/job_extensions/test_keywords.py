import pytest

from job_scrapper.sql.tables.job_extensions.keywords import Keywords
from job_scrapper.sql.tables.keywords.keyword_version import KeywordVersion
from .abstract_job_extra_base import TestJobExtraBase
from job_scrapper.sql.tables import Jobs
from job_scrapper.sql.tables.places.places import Places

@pytest.mark.js_tables
class TestKeywords(TestJobExtraBase):
    """Ensure that keyword table works as intended"""

    __tested_class__ = Keywords
    job_entry_name = "keywords_entries"
    db_comp1 = {"keyword": "download", "version": 1, "occurrence": 55}
    db_comp2 = {"keyword": "upload", "version": 1, "occurrence": None}
    db_comp3 = {
        "keyword": "download", "version": 1,
    }

    def make_small_database(
        self, screen_prefix: str = ""
    ):
        # Ensure that primary foreign keys are in database.
        with Keywords.get_session(self.standard_db_path()) as session:
            kv1 = KeywordVersion(
                keyword = self.db_comp1["keyword"],
                version = self.db_comp1["version"],
            )

            kv2 = KeywordVersion(
                keyword = self.db_comp2["keyword"],
                version = self.db_comp2["version"],
            )

            kv3 = KeywordVersion(
                keyword = self.db_comp3["keyword"],
                version = self.db_comp3["version"],
            )

            session.add(kv1)
            session.add(kv2)
            session.add(kv3)

        return super().make_small_database()

    def test_relationship__keyword_entries(self):
        """Test KeywordVersion.keyword_entries"""
        db = self.standard_db_path()
        ver1 = KeywordVersion(
            keyword="Alpha",
            version=1,
        )
        pl = Places(localisation=Jobs.DEFAULT_LOCALISATION)
        j1 = Jobs(
            url="TMP1",
        )
        j2 = Jobs(
            url="TMP2",
        )
        kw1 = Keywords(
            url="TMP1",
            keyword="Alpha",
            version=1,
            occurrence=33
        )
        kw2 = Keywords(
            url="TMP2",
            keyword="Alpha",
            version=1,
            occurrence=50
        )
        self.screen_var("miniVer1", ver1)
        self.screen_var("minikw1", kw1)
        self.screen_var("minikw2", kw2)

        ver1_bis = ver1.copy()
        kw1_bis = kw1.copy()
        kw2_bis = kw2.copy()
        self.screen_var("ver1_bis", ver1_bis)
        self.screen_var("kw1_bis", kw1_bis)
        self.screen_var("kw2_bis", kw2_bis)

        with KeywordVersion.get_session(db, logger=self.icl.logger) as session:
            session.add(pl)
            session.add(j1)
            session.add(j2)
            session.add(ver1)
            session.add(kw1)
            session.add(kw2)


        with KeywordVersion.get_session(db, logger=self.icl.logger) as session:
            ver1_from_db = ver1_bis.get_existing_self(session)
            self.screen_var("ver1_from_db", ver1_from_db)
            self.screen_multiple_vars("ver1_from_db.keyword_entries_", *ver1_from_db.keyword_entries)

            assert len(ver1_from_db.keyword_entries) == 2
            assert kw1_bis in ver1_from_db.keyword_entries
            assert kw2_bis in ver1_from_db.keyword_entries

    def test_relationship__available_version_entries(self):
        # == Build default database ==
        db = self.standard_db_path()
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
        pl = Places(localisation=Jobs.DEFAULT_LOCALISATION)
        j1 = Jobs(
            url="TMP1",
        )
        kw1 = Keywords(
            url="TMP1",
            keyword="Alpha",
            version=1,
            occurrence=33
        )
        self.screen_multiple_vars("ver{count}", ver1, ver2, ver3)
        self.screen_var("kw1", kw1)
        ver1_bis = ver1.copy()
        ver2_bis = ver2.copy()
        ver3_bis = ver3.copy()
        kw1_bis = kw1.copy()
        self.screen_multiple_vars("ver{count}_bis", ver1_bis, ver2_bis, ver3_bis)
        self.screen_var("kw1_bis", kw1_bis)

        with Keywords.get_session(db, logger=self.icl.logger) as session:
            session.add_all([pl, j1, ver1, ver2, ver3])
            session.add(kw1)
         # == Build default database ==

        with Keywords.get_session(db, logger=self.icl.logger) as session:
            all_version = KeywordVersion.get_available_versions(session, keyword=kw1_bis.keyword).all()
            self.screen_multiple_vars("Version", *all_version)

            # Does all_version contains the correct set of version entry
            assert ver1_bis in all_version
            assert ver2_bis in all_version
            assert ver3_bis not in all_version

            # Do we find the correct newest version ?
            newest_ver = KeywordVersion.get_newest_version(session, keyword=kw1_bis.keyword)
            self.screen_var("Newest", newest_ver)
            assert newest_ver.keyword == kw1_bis.keyword
            assert newest_ver == ver2_bis

