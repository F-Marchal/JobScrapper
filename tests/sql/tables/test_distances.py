from sql.tables.distances import Distances
from tests.conftest import BaseTest

class TestDistances(BaseTest):
    """Ensure that Distances table works as intended"""
    def test_get_job_associated_distances(self):
        """Test that <get_job_associated_distances> works as intended"""
        db1 = f"{self.test_folder}/database.db"
        d1 = Distances(
            reference_localisation="Paris",
            job_localisation="Paris",
            distance=0
        )
        d2 = Distances(
            reference_localisation="Paris",
            job_localisation="Strasbourg",
            distance=500
        )
        d3 = Distances(
            reference_localisation="Paris",
            job_localisation="Lyon",
            distance=500
        )
        d4 = Distances(
            reference_localisation="Lyon",
            job_localisation="Strasbourg",
            distance=500
        )
        self.screen_multiple_vars("D_obj", d1, d2, d3, d4)

        with Distances.get_session(db1) as session:
            session.add_all([d1, d2, d3, d4])
            # Commit

        with Distances.get_session(db1) as session:
            results = Distances.get_job_associated_distances(session, "Strasbourg")
            assert len(results) == 2

