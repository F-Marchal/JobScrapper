from tests.conftest import BaseTest
from sql.tables.jobs import Jobs
import pytest

@pytest.mark.js_tables
class TestJobs(BaseTest):
    """
    Ensure that Jobs table works as expected.

    Relationship test with JobExtraBase are exported to each JobExtraBase
    """

    def test_job_delete_cascade(self):
        """This test method should not test deletion cascade related to JobExtraBase"""
        # At this time, all deletion cascade are related to JobExtraBase"
        return

    def test_job_relationship(self):
        """This test method should not test relationship related to JobExtraBase"""
        # At this time, all relationship are related to JobExtraBase"
        return