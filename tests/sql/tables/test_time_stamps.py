from sql.tables.time_stamps import TimeStamps
from sql.tables.jobs import Jobs
from tests.conftest import BaseTest
import pytest
import datetime

@pytest.mark.js_tables
class TestTimeStamps(BaseTest):
    """Ensure that Distances table works as intended"""
    def test_get_job_associated_time_stamps(self):
        """Test that <get_job_associated_time_stamps> works as intended"""
        db1 = f"{self.test_folder}/database.db"
        with Jobs.get_session(db1) as session:
            session.add_all(self.make_small_database())

        with Jobs.get_session(db1) as session:
            assert 2 == len(TimeStamps.get_job_associated_time_stamps(session, "Alpha"))
            assert 1 == len(TimeStamps.get_job_associated_time_stamps(session, "Beta"))

    def test_relationship(self):
        """Ensure that the delete cascade works."""
        db_path = f"{self.test_folder}/database.db"
        db = self.make_small_database()

        assert isinstance(db[0], Jobs)  # Axiome
        url = db[0].url

        with Jobs.get_session(db_path) as session:
            session.add_all(db)

        with Jobs.get_session(db_path) as session:
            number_of_kw = len(TimeStamps.get_all(session).all())
            number_of_kw_associated_to_url = len(TimeStamps.get_job_associated_time_stamps(session, url=url))
            session.delete(db[0])

        # Now Only
        with Jobs.get_session(db_path) as session:
            # Ensure that passive_deletes works !
            assert len(TimeStamps.get_all(session).all()) == number_of_kw - number_of_kw_associated_to_url


    # Utils
    def make_small_database(self) -> list[Jobs | TimeStamps]:
        """Make a small database for test purposes."""
        j1 = Jobs(
            url="Alpha"
        )
        j2 = Jobs(
            url="Beta"
        )

        t1 = TimeStamps(
            url="Alpha",
            label="Download",
            time_stamp=datetime.datetime.now(),
        )
        t2 = TimeStamps(
            url="Alpha",
            label="Informatic",
            time_stamp=datetime.datetime.now(),
        )
        t3 = TimeStamps(
            url="Beta",
            label="Download",
            time_stamp=datetime.datetime.now(),
        )

        self.screen_multiple_vars("j", j1, j2)
        self.screen_multiple_vars("t", t1, t2, t3)

        return [j1, j2, t1, t2, t3]



