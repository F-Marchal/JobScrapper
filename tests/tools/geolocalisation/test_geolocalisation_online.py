from tools.geolocalisation import Places
from .base_test_geolocalisation import BaseGeoTest
import pytest
from tools.geolocalisation import Geolocalisation
from geopy.location import Location
from unittest.mock import patch

@pytest.mark.online_simulation
class TestGeolocalisationOnline(BaseGeoTest):
    """Test Geolocalisation's functionalities that require an internet connexion.
    Most function here require to mock (path) geocode request"""

    @patch("geopy.geocoders.Nominatim.geocode")
    def test_request__not_exist(self, mock_geocode):
        geo = self.make_geo()
        mock_geocode.return_value = None

        result = geo.request("Paris, France")
        assert result == (None, None)

    @patch("geopy.geocoders.Nominatim.geocode")
    def test_request__exist(self, mock_geocode):
        geo = self.make_geo()
        mock_geocode.return_value = Location(
            "Paris, France",
            (48.8566, 2.3522),
        {}
        )

        lat, lon = geo.request("Paris, France")

        assert lat == 48.8566
        assert lon == 2.3522

    @patch("geopy.geocoders.Nominatim.geocode")
    def test_geolocate__online(self, mock_geocode):
        """Test geolocate with default configuration"""
        geo = self.make_geo()

        # Default condition
        with Places.get_session(self.get_db_path(), logger=self.icl.logger) as session:
            mock_geocode.return_value = Location(
                "Paris, France",
                (48.8566, 2.3522),
                {}
            )
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
