import pytest

from tools.geolocalisation import Geolocalisation, Places

from .base_test_geolocalisation import BaseGeoTest


class TestGeolocalisation(BaseGeoTest):
    """Test Geolocalisation functions that does not require access to internet."""

    def test_get_localisation_from_database(self):
        """Test get_localisation_from_database"""
        with Places.get_session(
            self.get_db_path(), logger=self.icl.logger
        ) as session:
            result = Geolocalisation.get_localisation_from_database(
                session, "Paris, France"
            )
            assert result is None  # The database should be empty

        self.make_small_db()

        with Places.get_session(
            self.get_db_path(), logger=self.icl.logger
        ) as session:
            result = Geolocalisation.get_localisation_from_database(
                session, "Paris, France"
            )
            assert result is not None  # The database should be empty
            assert 2 < result.long < 2.8
            assert 48.2 < result.lat < 49.3

    def test_get_distances_from_database(self):
        """Test get_localisation_from_database"""
        with Places.get_session(
            self.get_db_path(), logger=self.icl.logger
        ) as session:
            result = Geolocalisation.get_distances_from_database(
                session, "Paris, France", "Knokke-le-Zoute, Belgium"
            )
            assert result is None  # The database should be empty

        self.make_small_db()

        with Places.get_session(
            self.get_db_path(), logger=self.icl.logger
        ) as session:
            result = Geolocalisation.get_distances_from_database(
                session, "Paris, France", "Knokke-le-Zoute, Belgium"
            )
            assert result is not None  # The database should be empty
            assert 300 < result.distance < 330

    @pytest.mark.parametrize(
        "entry1, entry2",
        [
            (
                Places(localisation="Alpha", longitude=0, latitude=None),
                Places(localisation="Beta", longitude=0, latitude=0),
            ),
            (
                Places(localisation="Alpha", longitude=None, latitude=0),
                Places(localisation="Beta", longitude=0, latitude=0),
            ),
            (
                Places(localisation="Alpha", longitude=0, latitude=0),
                Places(localisation="Beta", longitude=None, latitude=0),
            ),
            (
                Places(localisation="Alpha", longitude=0, latitude=0),
                Places(localisation="Beta", longitude=0, latitude=None),
            ),
            (
                Places(localisation="Alpha", longitude=None, latitude=None),
                Places(localisation="Beta", longitude=0, latitude=0),
            ),
            (
                Places(localisation="Alpha", longitude=0, latitude=0),
                Places(localisation="Beta", longitude=None, latitude=None),
            ),
        ],
    )
    def test_compute_distance__invalid_place_obj(
        self, entry1: Places, entry2: Places
    ):
        """Ensure that compute_distance returns None in certain situations"""
        geo = self.make_geo()
        l1 = entry1.localisation
        l2 = entry2.localisation

        self.screen_var("l1", entry1)
        self.screen_var("l2", entry2)

        with Places.get_session(
            self.get_db_path(), logger=self.icl.logger
        ) as session:
            session.add(entry1)
            session.add(entry2)

        with Places.get_session(
            self.get_db_path(), logger=self.icl.logger
        ) as session:
            result = geo.compute_distance(
                session,
                l1,
                l2,
            )

        assert result is None

    def test_compute_distance__valid_place_obj(self):
        """Ensure that compute distance works with a valid database."""
        geo = self.make_geo()
        self.make_small_db()

        with Places.get_session(
            self.get_db_path(), logger=self.icl.logger
        ) as session:
            result = geo.compute_distance(
                session,
                "Paris, France",
                "Knokke-le-Zoute, Belgium",
            )

        assert 300 < result < 330
