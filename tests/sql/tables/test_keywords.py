from sql.tables.keywords import Keywords
from sql.tables.jobs import Jobs
from tests.conftest import BaseTest
import pytest

@pytest.mark.js_tables
class TestKeywords(BaseTest):
    """Ensure that Distances table works as intended"""
    def test_get_job_associated_keywords(self):
        """Test that <get_job_associated_keywords> works as intended"""
        db1 = f"{self.test_folder}/database.db"
        with Jobs.get_session(db1) as session:
            session.add_all(self.make_small_database())

        with Jobs.get_session(db1) as session:
            assert 2 == len(Keywords.get_job_associated_keywords(session, "Alpha"))
            assert 1 == len(Keywords.get_job_associated_keywords(session, "Beta"))

    def test_relationship(self):
        """Ensure that the delete cascade works."""
        db_path = f"{self.test_folder}/database.db"
        db = self.make_small_database()

        assert isinstance(db[0], Jobs)  # Axiome
        url = db[0].url

        with Jobs.get_session(db_path) as session:
            session.add_all(db)

        with Jobs.get_session(db_path) as session:
            number_of_kw = len(Keywords.get_all(session).all())
            number_of_kw_associated_to_url = len(Keywords.get_job_associated_keywords(session, url=url))
            session.delete(db[0])

        # Now Only
        with Jobs.get_session(db_path) as session:
            # Ensure that passive_deletes works !
            assert len(Keywords.get_all(session).all()) == number_of_kw - number_of_kw_associated_to_url


    # Utils
    def make_small_database(self) -> list[Keywords | Jobs]:
        """Make a small database for test purposes."""
        j1 = Jobs(
            url="Alpha"
        )
        j2 = Jobs(
            url="Beta"
        )

        k1 = Keywords(
            url="Alpha",
            keyword="Biology",
            occurrence=45,
        )
        k2 = Keywords(
            url="Alpha",
            keyword="Informatic",
            occurrence=5,
        )
        k3 = Keywords(
            url="Beta",
            keyword="Biology",
            occurrence=None,
        )

        self.screen_multiple_vars("j", j1, j2)
        self.screen_multiple_vars("k", k1, k2, k3)

        return [j1, j2, k1, k2, k3]



