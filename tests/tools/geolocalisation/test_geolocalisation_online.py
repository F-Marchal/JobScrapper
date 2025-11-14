from tools.geolocalisation import Places
from .base_test_geolocalisation import BaseGeoTest
import pytest
from tools.geolocalisation import Geolocalisation

@pytest.mark.online_simulation
class TestGeolocalisationOnline(BaseGeoTest):
    """Test Geolocalisation's functionalities that require an internet connexion."""
    def test_request__online(self):
        """Test to request coordinate of an existing and a non-existing place."""
        geo = self.make_geo()
        lat, long = geo.request("Paris, France")
        failed = geo.request("A place name that, obviously, does not exist")

        assert 48.2 < lat < 49.3
        assert 2 < long <  2.8
        assert failed == (None, None)

    def test_geolocate__online(self):
        """Test geolocate with default configuration"""
        geo = self.make_geo()

        # Default condition
        with Places.get_session(self.get_db_path(), logger=self.icl.logger) as session:
            lat, long = geo.geolocate(session, "Paris, France")

        assert lat is not None
        assert long is not None
        assert 48.2 < lat < 49.3
        assert 2 < long <  2.8

        # Does Paris have been added
        expected_in_database = Places(
            localisation="Paris, France",
        )
        with Places.get_session(self.get_db_path(), logger=self.icl.logger) as session:
            assert expected_in_database.exists(session)
            existing =  expected_in_database.get_existing_self(session)

            assert 48.2 < existing.lat < 49.3
            assert 2 <  existing.long < 2.8
