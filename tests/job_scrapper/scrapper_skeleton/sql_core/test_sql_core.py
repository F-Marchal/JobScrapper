import os

import pytest
from tests.conftest import BaseTest

from job_scrapper.scrapper_skeleton.sql_core.sql_core import ScrapperSQLightCore


@pytest.mark.job_core
class TestScrapperObjectCore(BaseTest):
    """Test ScrapperObjectCore main functionalities."""

    def test_sql_compatible_header_keyword(self):
        assert "edouard_IV" == ScrapperSQLightCore.sql_header_compatible_string("édouard IV")
        assert "3" == ScrapperSQLightCore.sql_header_compatible_string("<3")
        assert "Unable_to_use_as_header" == ScrapperSQLightCore.sql_header_compatible_string("**--/*/*")

        # Ensure that default string is usable as header
        default_string = ScrapperSQLightCore.sql_header_compatible_string("**--/*/*")
        assert default_string == ScrapperSQLightCore.sql_header_compatible_string(default_string)

    def test_class_variable(self):
        """Ensure that table names can be used as table name in sqlite."""
        sslq = ScrapperSQLightCore
        assert sslq.main_table_name == sslq.sql_header_compatible_string(sslq.main_table_name)
        assert sslq.metadata_table_name == sslq.sql_header_compatible_string(sslq.metadata_table_name)
        assert sslq.keywords_table_name == sslq.sql_header_compatible_string(sslq.keywords_table_name)
        assert sslq.distances_table_name == sslq.sql_header_compatible_string(sslq.distances_table_name)
        assert sslq.time_stamps_table_name == sslq.sql_header_compatible_string(sslq.time_stamps_table_name)

    def test_database_creation(self):
        """ Ensure that a database is generated with write_in_database.
        Here to detect errors during the execution, not to test the content of the database"""
        assert not os.path.exists(ScrapperSQLightCore.get_database_path())

        # Database creation
        with ScrapperSQLightCore.write_in_database():
            pass

        # Database reopened
        with ScrapperSQLightCore.write_in_database():
            pass

        assert os.path.exists(ScrapperSQLightCore.get_database_path())

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
        ssc1_a = self._generate_a_test_ssc("SSC1-B")
        ssc2_a = self._generate_a_test_ssc("SSC2-B")
        ssc2_a.field = None

        # The null case !
        ssc3_a = ScrapperSQLightCore("")
        ssc3_a.add_keyword_count("", 5)
        ssc3_a.add_distance_to("", 5)
        ssc3_a.add_time_stamps("", ssc3_a.now())
        ssc3_a.add_metadata("", "")
        ssc3_a.add_metadata("o", "b")
        self.screen_var("SSC3-A", ssc3_a)

        ssc1_a.sql_export()
        ssc2_a.sql_export()
        ssc3_a.sql_export()

        ssc1_a.logger.critical(ssc1_a.sql_run_with_header())

        assert False