from tests.conftest_offline import OfflineTestClass
from job_scrapper.tools.geolocalisation import Geolocalisation, Places

from .base_test_geolocalisation import BaseGeoTest


class TestGeolocalisationOffline(BaseGeoTest, OfflineTestClass):
    """Test Geolocalisation's functionalities that require an internet connexion
    when no internet connexion is provided."""

    def make_geo(self):
        geo = Geolocalisation(
            contact=f"{self.user_agent}-Pytest-{type(self).__name__}",
            logger=self.icl.logger,
            timeout=15,
            error_wait_seconds=16,
        )
        self.screen_var("geo", geo)
        return geo

    def test_request__offline(self):
        """Test request with no internet connexion"""
        geo = self.make_geo()
        paris = geo.request("Paris, France")
        assert paris == (None, None)

    def test_geolocate__offline(self):
        """Test geolocate with no internet connexion"""
        geo = self.make_geo()

        # No error raised
        with Places.get_session(
            self.get_db_path(), logger=self.icl.logger
        ) as session:
            lat, long = geo.geolocate(session, "Paris, France")

        assert lat is None
        assert long is None

        self.make_small_db()

        # Ensure lazy works as intended
        with Places.get_session(
            self.get_db_path(), logger=self.icl.logger
        ) as session:
            lat, long = geo.geolocate(session, "Paris, France")

        assert lat is not None
        assert long is not None
        assert 2 < long < 2.8
        assert 48.2 < lat < 49.3
