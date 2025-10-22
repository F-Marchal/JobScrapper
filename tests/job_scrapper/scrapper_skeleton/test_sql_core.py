import os

import pytest
from tests.conftest import BaseTest

from job_scrapper.scrapper_skeleton.sql_core import ScrapperSQLightCore


@pytest.mark.job_core
class TestScrapperSQLightCore(BaseTest):
    """Test ScrapperSQLightCore main functionalities."""

    @pytest.fixture(autouse=True)
    def _redirect_logs(self, _setup_tempdir):
        path = os.path.join(self.test_folder, "scrapper.logs")
        with open(path, "w", encoding="UTF8") as f :
            with ScrapperSQLightCore.redirect_logs_to_file( f , level="DEBUG"):
                yield path



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


