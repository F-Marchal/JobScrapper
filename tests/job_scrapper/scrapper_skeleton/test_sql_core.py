import os
import time
import pytest

from job_scrapper.scrapper_skeleton.sql_core import ScrapperSQLightCore, KeywordVersion
from tests.job_scrapper.js_base_test import JobScrapperBaseTestClass
NOW = ScrapperSQLightCore.now()

#TODO: test __init__: load_job_entry, load_keywords ...
#TODO: load_job_entry_from_db, load_keywords_from_db, ...

class TestScrapperSQLightCore(JobScrapperBaseTestClass):
    """Test ScrapperSQLightCore main functionalities."""
    icl = ScrapperSQLightCore

    def get_scrapper(self):
        return ScrapperSQLightCore

    def test_to_job_entry(self):
        """Ensure correct conversion of a ScrapperSQLightCore
        into a Jobs entry."""
        ssc = self._generate_a_test_ssc()
        entry = ssc.to_job_entry()

        assert entry.url == ssc.url
        assert entry.title == ssc.title
        assert entry.localisation == ssc.localisation
        assert entry.contract == ssc.contract_type
        assert entry.field == ssc.field
        assert entry.origin == ssc.get_standardised_class_name()

    def test_to_metadata_entries(self):
        """Test the generation of Metadata entries from
        an object"""
        ssc = self._generate_a_test_ssc()
        entries = ssc.to_metadata_entries()

        self.screen_multiple_vars("entry", *entries)
        entry_d = {ent.key: ent.value for ent in entries}
        assert entry_d == ssc.metadata

    def test_to_keywords_entries__no_ver(
        self,
    ):
        """Test the generation of Keywords entries from
        an object"""
        ssc = self._generate_a_test_ssc()
        key_ver_entries = ssc.to_keywords_entries()

        self.screen_multiple_vars("key_ver_entries", *key_ver_entries)
        restructured_keyword_dict = {

        }
        for (ver, keyw) in key_ver_entries:
            assert ver.version == keyw.version
            assert ver.keyword == keyw.keyword
            restructured_keyword_dict[keyw.keyword] = keyw.occurrence if keyw.occurrence is not None else -1
        self.screen_var("restructured_keyword_dict", restructured_keyword_dict)
        assert restructured_keyword_dict == ssc.keywords

    def test_to_keywords_entries__with_ver(
        self,
    ):
        """Test the generation of Keywords entries from
        an object and a keywords_ver"""
        ssc = self._generate_a_test_ssc()

        # Version entry
        inf_version = KeywordVersion(keyword="Informatics", version=42)
        ver_dict = {
            inf_version.keyword: inf_version
        }
        self.screen_multiple_vars("inf_version", inf_version)

        # Keywords entries
        key_ver_entries = ssc.to_keywords_entries(**ver_dict)
        self.screen_multiple_vars("key_ver_entries", *key_ver_entries)
        keyword_ver_entries,  keyword_entries = zip(*key_ver_entries)
        self.screen_var("keyword_ver_entries", keyword_ver_entries)
        self.screen_var("keyword_entries", keyword_entries)

        # Test keywords entries
        assert inf_version in keyword_ver_entries

    def test_to_time_stamps_entries(
        self,
    ):  # IA generated from test_to_metadata_entries
        """Test the generation of TimeStamp entries from
        an object"""
        ssc = self._generate_a_test_ssc()
        entries = ssc.to_time_stamps_entries()

        self.screen_multiple_vars("entry", *entries)
        entry_d = {ent.label: ent.time_stamp.timetuple() for ent in entries}

        # Compare struct_time values (tm_year, tm_mon, etc.)
        expected = ssc.time_stamps
        for label, t_struct in expected.items():
            e_time = entry_d[label]
            assert (
                e_time.tm_year == t_struct.tm_year
                and e_time.tm_mon == t_struct.tm_mon
                and e_time.tm_mday == t_struct.tm_mday
                and e_time.tm_hour == t_struct.tm_hour
                and e_time.tm_min == t_struct.tm_min
                and e_time.tm_sec == t_struct.tm_sec
            )

    def test_to_distances_entries(
        self,
    ):  # IA generated from test_to_metadata_entries
        """Test the generation of distances entries from
        an object"""
        ssc = self._generate_a_test_ssc()
        entries = ssc.to_distances_entries()

        self.screen_multiple_vars("entry", *entries)
        entry_d = {
            ent.reference_localisation: (
                ent.distance if ent.distance is not None else -1
            )
            for ent in entries
        }
        assert entry_d == ssc.distances

    def test_initialisation_time_stamp_fetch(self):
        """Ensure that the first_sighting_time_stamp_name time stamp is correctly fetch
        during object initialization"""
        ssc1_a = self._generate_a_test_ssc("ssc1_a")
        now = ScrapperSQLightCore.now()
        tn = ssc1_a.first_sighting_time_stamp_name

        diff_time = time.mktime(ssc1_a.retrieve_time_stamps(tn)) - time.mktime(now)
        assert diff_time < 30

    def test_class_variable(self):
        """Ensure that table names can be used as table name in sqlite."""
        for table_name, table in ScrapperSQLightCore.get_all_tables().items():
            assert table_name == table.__tablename__

        # _database_file_name
        # _databases
        # first_sighting_time_stamp_name


    @pytest.mark.parametrize(
        "database_name, expected_path_cmd",
        [
            ("maindb", ScrapperSQLightCore.get_maindb_path),
            (None, ScrapperSQLightCore.get_maindb_path),
            ("archive", ScrapperSQLightCore.get_archive_path),
        ],
    )
    def test_database_creation(
            self,
            database_name: str,
            expected_path_cmd
    ):
        """Ensure that a database is generated with get_database_session.
        Here to detect errors during the execution, not to test the content of the database
        """

        expected_path = expected_path_cmd()
        assert not os.path.exists(expected_path)

        # Database creation
        with ScrapperSQLightCore.get_sql_session(database_name=database_name):
            pass

        # Database reopened
        with ScrapperSQLightCore.get_sql_session(database_name=database_name):
            pass

        assert os.path.exists(expected_path)

    def test_archive_creation(self):
        """Ensure that an archive database is generated with get_archive_session.
        Here to detect errors during the execution, not to test the content of the database
        """
        assert not os.path.exists(ScrapperSQLightCore.get_archive_path())

        # Database creation
        with ScrapperSQLightCore.get_archive_session():
            pass

        # Database reopened
        with ScrapperSQLightCore.get_archive_session():
            pass

        assert os.path.exists(ScrapperSQLightCore.get_archive_path())

    def test_export_import_object(self):
        """Test the import method of ScrapperSQLightCore"""
        ssc1_a = self._generate_a_test_ssc("SSC1-A")
        ssc2_a = self._generate_a_test_ssc("SSC2-A")
        ssc2_a.field = None

        # The null case !
        ssc3_a = ScrapperSQLightCore("")
        ssc3_a.add_keyword_count("", 5)
        ssc3_a.add_distance_to("", 5)
        ssc3_a.add_time_stamps("", ssc3_a.now())
        ssc3_a.add_metadata("", "")
        ssc3_a.add_metadata("o", "b")
        self.screen_var("SSC3-A", ssc3_a)

        with ScrapperSQLightCore.get_sql_session() as session:
            ssc1_a.sql_export(session)

        ScrapperSQLightCore.sql_batch_export(
            ssc2_a,
            ssc3_a,
        )

        with ScrapperSQLightCore.get_sql_session() as session:
            reloaded_ssc = sorted(
                ScrapperSQLightCore.sql_import_jobs(session),
                key=lambda j: {
                    "https://SSC1-A.fr": 1,
                    "https://SSC2-A.fr": 2,
                    "": 3
                }[j.url]
            )

        assert len(reloaded_ssc) == 3
        # pylint: disable=w0632
        # previous assertion ensure that reloaded_ssc contains 3 element
        ssc1_b, ssc2_b, ssc3_b = reloaded_ssc

        self.tracker.write("\nComparison\n")
        self.tracker.screen("SSC1-B", ssc1_b)
        self.re_screen_var("SSC1-A")
        self.tracker.write("\n\n")
        self.tracker.screen("SSC2-B", ssc2_b)
        self.re_screen_var("SSC2-A")
        self.tracker.write("\n\n")
        self.tracker.screen("SSC3-B", ssc3_b)
        self.re_screen_var("SSC3-A")

        assert ssc1_b == ssc1_a
        assert ssc2_b == ssc2_a
        assert ssc3_b == ssc3_a

    def test_job_requester(self):
        """job_requester is tested inside its own file :
        tests/sql/tables/helpers/test_job_request.py"""

    def _generate_a_test_ssc(
        self, instance_name: str = "SSC",
    ) -> ScrapperSQLightCore:
        ssc = ScrapperSQLightCore(
            f"https://{instance_name}.fr",
            title=f"Work in {instance_name}",
            localisation="Rouen, france",
            contract_type="CDI",
            field="Biology",
        )
        ssc.add_metadata("Message", "<3")
        ssc.add_metadata("Account :", "9 \t000")
        ssc.add_distance_to("Paris, france", 100.678)
        ssc.add_time_stamps("Test time", NOW)
        ssc.add_keyword_count("Informatics", 45)

        # Collision and default value
        ssc.add_keyword_count("Strasbourg", -1)
        ssc.add_distance_to("Strasbourg", -1)
        ssc.add_time_stamps("Strasbourg", NOW)

        self.tracker.screen(instance_name, ssc)

        return ssc
