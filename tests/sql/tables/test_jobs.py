import pytest

from sql.tables.jobs import Jobs
from sql.tables.places.places import Places
from tests.conftest import BaseTest


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

    def test_default_value(self):
        """Ensure that Jobs.DEFAULT_LOCALISATION is compatible with both Jobs and Places"""
        default_place = Places(
            localisation = Jobs.DEFAULT_LOCALISATION
        )
        default_job = Jobs(
            url = "TMP",
            localisation = Jobs.DEFAULT_LOCALISATION
        )

        self.screen_var("Default localisation", Jobs.DEFAULT_LOCALISATION)
        self.screen_var("Jobs", default_job)
        self.screen_var("Place", default_place)

        assert default_place.localisation == default_job.localisation
        assert default_place.localisation == Jobs.DEFAULT_LOCALISATION
        assert default_job.localisation == Jobs.DEFAULT_LOCALISATION
