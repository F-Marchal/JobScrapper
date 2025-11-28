from tests.conftest import BaseTest
from sql.tables.places.places import Places, Jobs
import pytest
import sqlalchemy.exc as exc

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

    def test_place_constraint_failure(self):
        """Ensure that a job can not be added to the database if the localisation
        is unknown."""
        j1 = Jobs(url="Alpha", localisation="Paris, France")
        self.screen_var("j1", j1)

        # Expect IntegrityError :
        # Alpha not in Places
        with pytest.raises(exc.IntegrityError):
            with Jobs.get_session("db1.db") as session:
                    session.add(j1)

    def test_place_constraint_success(self):
        """Ensure that a job can be added to the database if the localisation
        is known."""
        p1 = Places(
            localisation="Paris, France",
            longitude=48.85341,
            latitude=2.3488,
        )
        self.screen_var("p1", p1)
        j1 = Jobs(url="Alpha", localisation="Paris, France")
        self.screen_var("j1", j1)

        with Jobs.get_session("db1.db") as session:
            session.add(p1)
            session.add(j1)

    def test_get_column_distance_to_self(self):
        """Ensure that get_column_distance_to_self works with and without filter."""
        p1 = Places(
            localisation="Paris, France",
            longitude=48.85341,
            latitude=2.3488,
        )
        p2 = Places(
            localisation="Strasbourg, France",
            longitude=48.583328,
            latitude=7.75 ,
        )
        self.screen_multiple_vars("p", p1, p2)

        j1 = Jobs(url="Alpha", localisation="Paris, France")
        j2 = Jobs(url="Beta", localisation="Paris, France")
        j3 = Jobs(url="Gamma", localisation="Strasbourg, France")
        self.screen_multiple_vars("j", j1, j2, j3)

        with Jobs.get_session("db1.db") as session:
            session.add(p1)
            session.add(p2)
            session.add(j1)
            session.add(j2)
            session.add(j3)

        with Jobs.get_session("db1.db") as session:
            # Find entry in database
            p_strasbourg = session.query(Places).filter_by(localisation="Strasbourg, France").first()
            p_paris = session.query(Places).filter_by(localisation="Paris, France").first()

            paris_col = p_paris.get_column_distance_to_self()
            strasbourg_col = p_strasbourg.get_column_distance_to_self()

            query = session.query(
                Jobs.url,
                Jobs.localisation,
                paris_col,
                strasbourg_col,
            )

            query = query.join(Jobs.places_entry) # Join Jobs on Places

            for (url, local, dist_paris, dist_strasbourg) in query.all():
                self.tracker.write(f"{url}\t{local}\t{dist_strasbourg}\t{dist_paris}")

                if url in ["Alpha", "Beta"]:
                    assert 600 < dist_strasbourg < 605
                    assert dist_paris == 0
                else:
                    assert 600 < dist_paris < 605
                    assert dist_strasbourg == 0

            self.tracker.write("Filtered query")
            query = query.filter(
                paris_col <= 50
            )

            for (url, local, dist_paris, dist_strasbourg) in query.all():
                self.tracker.write(f"{url}\t{local}\t{dist_strasbourg}\t{dist_paris}")
                assert dist_paris <= 50

    def test_get_column_nearest_place_to(self):
        """Ensure that get_column_nearest_place_to works"""
        p1 = Places(
            localisation="Paris, France",
            longitude=48.85341,
            latitude=2.3488,
        )
        p2 = Places(
            localisation="Strasbourg, France",
            longitude=48.583328,
            latitude=7.75 ,
        )
        self.screen_multiple_vars("p", p1, p2)

        j1 = Jobs(url="Alpha", localisation="Paris, France")
        j2 = Jobs(url="Beta", localisation="Paris, France")
        j3 = Jobs(url="Gamma", localisation="Strasbourg, France")
        self.screen_multiple_vars("j", j1, j2, j3)

        with Jobs.get_session("db1.db") as session:
            session.add(p1)
            session.add(p2)
            session.add(j1)
            session.add(j2)
            session.add(j3)

        with Jobs.get_session("db1.db") as session:
            # Find entry in database
            p_strasbourg = session.query(Places).filter_by(localisation="Strasbourg, France").first()
            p_paris = session.query(Places).filter_by(localisation="Paris, France").first()

            place_col, km_col = Places.get_column_nearest_place_to(
                'Nearest place',
                p_paris,
                p_strasbourg
            )


            query = session.query(
                Jobs.url,
                Jobs.localisation,
                place_col,
                km_col,
            )

            query = query.join(Jobs.places_entry) # Join Jobs on Places

            for (url, local, place, dist) in query.all():
                self.tracker.write(f"{url}\t{local}\t{place}\t{dist}")
                assert dist < 50

                if url in ["Alpha", "Beta"]:
                    assert place == "Paris, France"
                else:
                    assert place == "Strasbourg, France"
