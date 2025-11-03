import os

import pytest
from tests.conftest import BaseTest
from job_scrapper.scrapper_skeleton.sql_core import ScrapperSQLightCore


@pytest.mark.job_core
class TestScrapperSQLightCore(BaseTest):
    """Test ScrapperSQLightCore main functionalities."""
    icl = ScrapperSQLightCore

    def test_to_job_entry(self):
        ssc = self._generate_a_test_ssc()
        entry = ssc.to_job_entry()

        assert entry.url == ssc.url
        assert entry.title == ssc.title
        assert entry.localisation == ssc.localisation
        assert entry.contract == ssc.contract_type
        assert entry.field == ssc.field
        assert entry.origin == ssc.get_class_name()

    def test_to_metadata_entries(self):
        ssc = self._generate_a_test_ssc()
        entries = ssc.to_metadata_entries()

        self.screen_multiple_vars("entry", *entries)
        entry_d = {ent.key : ent.value for ent in entries}
        assert entry_d == ssc.metadata

    def test_to_keywords_entries(self):  # IA generated from test_to_metadata_entries
        ssc = self._generate_a_test_ssc()
        entries = ssc.to_keywords_entries()

        self.screen_multiple_vars("entry", *entries)
        entry_d = {ent.keyword: (ent.occurrence if ent.occurrence is not None else -1)
                   for ent in entries}
        assert entry_d == ssc.keywords

    def test_to_time_stamps_entries(self):  # IA generated from test_to_metadata_entries
        ssc = self._generate_a_test_ssc()
        entries = ssc.to_time_stamps_entries()

        self.screen_multiple_vars("entry", *entries)
        entry_d = {
            ent.label: ent.time_stamp.timetuple()
            for ent in entries
        }

        # Compare struct_time values (tm_year, tm_mon, etc.)
        expected = ssc.time_stamps
        for label, t_struct in expected.items():
            e_time = entry_d[label]
            assert (
                    e_time.tm_year == t_struct.tm_year and
                    e_time.tm_mon == t_struct.tm_mon and
                    e_time.tm_mday == t_struct.tm_mday and
                    e_time.tm_hour == t_struct.tm_hour and
                    e_time.tm_min == t_struct.tm_min and
                    e_time.tm_sec == t_struct.tm_sec
            )

    def test_to_distances_entries(self): # IA generated from test_to_metadata_entries
        ssc = self._generate_a_test_ssc()
        entries = ssc.to_distances_entries()

        self.screen_multiple_vars("entry", *entries)
        entry_d = {
            ent.reference_localisation:
                (ent.distance if ent.distance is not None else -1)
            for ent in entries
        }
        assert entry_d == ssc.distances

    def test_class_variable(self):
        """Ensure that table names can be used as table name in sqlite."""
        for table_name, table in ScrapperSQLightCore.get_tables().items():
            assert table_name == table.__tablename__

        # _database_file_name
        # _databases
        # first_sighting_time_stamp_name


    def test_database_creation(self):
        """ Ensure that a database is generated with get_database_session.
        Here to detect errors during the execution, not to test the content of the database"""
        assert not os.path.exists(ScrapperSQLightCore.get_maindb_path())

        # Database creation
        with ScrapperSQLightCore.get_maindb_session():
            pass

        # Database reopened
        with ScrapperSQLightCore.get_maindb_session():
            pass

        assert os.path.exists(ScrapperSQLightCore.get_maindb_path())

    def test_archive_creation(self):
        """ Ensure that an archive database is generated with get_archive_session.
        Here to detect errors during the execution, not to test the content of the database"""
        assert not os.path.exists(ScrapperSQLightCore.get_archive_path())

        # Database creation
        with ScrapperSQLightCore.get_archive_session():
            pass

        # Database reopened
        with ScrapperSQLightCore.get_archive_session():
            pass

        assert os.path.exists(ScrapperSQLightCore.get_archive_path())

    def _generate_a_test_ssc(
        self, instance_name: str = "SSC"
    ) -> ScrapperSQLightCore:
        ssc = ScrapperSQLightCore(
            f"https://{instance_name}.fr",
            title=f"Work in {instance_name}",
            localisation="Rouen, france",
            contract_type="CDI",
            field="Biology",
        )
        now = ssc.now()
        ssc.add_metadata("Message", "<3")
        ssc.add_metadata("Account :", "9 \t000")
        ssc.add_distance_to("Paris, france", 100.678)
        ssc.add_time_stamps("Test time", now)
        ssc.add_keyword_count("Informatics", 45)

        # Collision and default value
        ssc.add_keyword_count("Strasbourg", -1)
        ssc.add_distance_to("Strasbourg", -1)
        ssc.add_time_stamps("Strasbourg", now)

        self.tracker.screen(instance_name, ssc)

        return ssc

    def test_export_import_object(self):
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

        with ScrapperSQLightCore.get_maindb_session() as session:
            ssc1_a.sql_export(session)
            ssc2_a.sql_export(session)
            ssc3_a.sql_export(session)

        with ScrapperSQLightCore.get_maindb_session() as session:
           reloaded_ssc = ScrapperSQLightCore.sql_import_jobs(session)

        assert len(reloaded_ssc) == 3

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
        tests/sql/tables/request_helpers/test_job_request.py"""

