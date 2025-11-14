from tests.conftest_mandatory_identifier import MandatoryIdentifierTestClass
import os
from tools.geolocalisation import Geolocalisation, Places, Distances


class BaseGeoTest(MandatoryIdentifierTestClass):
    """Base class for Geolocalisation related tests"""
    def make_geo(self):
        """Generate a Geolocalisation object"""
        geo = Geolocalisation(
            contact=f"{self.user_agent}-Pytest-{type(self).__name__}",
            logger=self.icl.logger,
            timeout=300,
        )
        self.screen_var("geo", geo)
        return geo

    def get_db_path(self) -> str:
        """Give the path of the database used during test."""
        return os.path.join(self.test_folder, "geo.db")

    def make_small_db(self):
        """Generate a small database that contains a few Places / Distances"""
        with Distances.get_session(self.get_db_path(), logger=self.icl.logger) as session:
            session.add_all(
                [
                Places(
                    localisation="Paris, France",
                    latitude=48.85341,
                    longitude=2.3488,
                ),
                Places(
                    localisation="Knokke-le-Zoute, Belgium",
                    latitude=51.35,
                    longitude=3.26667,
                ),

                Distances(
                    reference_localisation="Paris, France",
                    job_localisation="Knokke-le-Zoute, Belgium",
                    distance=315
                )
                ]
            )

        return Geolocalisation





