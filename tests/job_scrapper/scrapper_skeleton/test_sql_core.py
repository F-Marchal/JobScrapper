import os

import pytest
from tests.conftest import BaseTest

from job_scrapper.scrapper_skeleton.sql_core import ScrapperSQLightCore


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
