from tests.conftest import BaseTest
from sql.tables.places.places import Places

class TestPlaces(BaseTest):
    def test_lat(self):
        pl = Places(
            localisation="Anywhere",
            longitude = 5.202,
            latitude = 6.358,
        )
        self.screen_var("pl", pl)

        assert pl.lat == 6.358

    def test_long(self):
        pl = Places(
            localisation="Anywhere",
            longitude = 5.202,
            latitude = 6.358,
        )
        self.screen_var("pl", pl)

        assert pl.long == 5.202

    def test_coord(self):
        pl = Places(
            localisation="Anywhere",
            longitude = 5.202,
            latitude = 6.358,
        )
        self.screen_var("pl", pl)

        assert pl.coord == (6.358, 5.202)

    def test_is_computable(self):
        pl1 = Places(
            localisation="Anywhere",
            longitude = 5.202,
            latitude = 6.358,
        )
        pl2 = Places(
            localisation="Anywhere",
            longitude = None,
            latitude = 6.358,
        )
        pl3 = Places(
            localisation="Anywhere",
            longitude = 5.202,
            latitude = None,
        )
        pl4 = Places(
            localisation="Anywhere",
            longitude = None,
            latitude = None,
        )

        self.screen_multiple_vars("pl", pl1, pl2, pl3, pl4)

        assert pl1.is_computable()
        assert not pl2.is_computable()
        assert not pl3.is_computable()
        assert not pl4.is_computable()
