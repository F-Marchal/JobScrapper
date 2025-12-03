"""
This Table replace the Distance table. Distances will now be calculated at
runtime to avoid having this HUGE table that require the use of
'reference' localisation.


# 28/11/2025 (Marchal)
def create_distance_column(...):
    I Hesitated to use something like :
    ```
    if label is None:
        label = str(self.localisation)

    return Places.sql_distance(
        Places.latitude, Places.longitude,
        self.latitude, self.longitude
    ).label(label)

distance_to_a_place_column = place.create_distance_column(label)
qquery  query.add_columns(distance_to_a_place_column)

But it appears that for multiple columns, this will not be as efficient as to use
a case (require multiple joins).
```
"""
from sqlalchemy import Column, Float, String, func, ColumnElement, case, Label
from sqlalchemy.orm import relationship, Session, validates

from sql.tables.base_table import BaseTable
from sql.tables.jobs import Jobs

EARTH_RADIUS = 6371.0

class Places(BaseTable):
    """Contains a number of reference places coordinates."""

    __abstract__ = False
    __tablename__ = "places"

    localisation = Column(String, primary_key=True, nullable=False)
    longitude = Column(Float, nullable=True)
    latitude = Column(Float, nullable=True)

    jobs_entry = relationship("Jobs", back_populates="places_entry")

    @validates("localisation")
    def _validate_localisation(self, key, value):
        return self.format_localisation(value)

    @staticmethod
    def format_localisation(string: str) -> str:
        """Format localisation column"""
        return string.strip().title()

    @property
    def lat(self) -> float | None:
        return getattr(self, "latitude")

    @property
    def long(self) -> float | None:
        return getattr(self, "longitude")

    @property
    def coord(self) -> tuple[float | None, float | None]:
        return self.lat, self.long

    def is_computable(self) -> bool:
        return self.lat is not None and self.long is not None

    @staticmethod
    def sql_distance( # AI Generated
        lat1: ColumnElement[float],
        lon1: ColumnElement[float],
        lat2: ColumnElement[float],
        lon2: ColumnElement[float],
        round_: float = 3
    ):
        """
        Return SQL expression for the distance between (lat1, lon1) and (lat2, lon2) in km.
        Can be used in queries.
        """
        x = (
                func.cos(func.radians(lat1)) *
                func.cos(func.radians(lat2)) *
                func.cos(func.radians(lon2) - func.radians(lon1)) +
                func.sin(func.radians(lat1)) *
                func.sin(func.radians(lat2))
        )

        # Ensure x  [-1, 1] to avoid acos domain errors
        x_clamped = case(
            (x > 1, 1),
            (x < -1, -1),
            else_=x
        )

        distance_expr = EARTH_RADIUS * func.acos(x_clamped)

        # Round distances smaller than 0.001 km as 0
        distance_expr = case(
            (distance_expr < 0.001, 0),
            else_=distance_expr
        )

        return  func.round(distance_expr, round_)

    def get_column_distance_to_self(self, label: str | None = None, round_: int=3) -> Label:
        """
        Returns a sql expression that compute the distance to this reference place for all jobs.

        # Assuming "Paris, France" in database.
        reference_place = session.get(Places, "Paris, France")
        distance_expr = reference_place.get_distance_to_self_column()

        query = (
            session.query(Jobs, distance_expr)
            .join(Places, Jobs.localisation == Places.localisation)
            .filter(distance_expr <= 50)  # distance in km
        )

        :param label: A Label for this column. Default : self.localisation + " KM"
        :param round_: Round to [round_] digit after '.'
        """
        if label is None:
            label = self.localisation + " KM"
        return Places.sql_distance(
            lat1=self.latitude,
            lon1=self.longitude,
            lat2=Places.latitude,
            lon2=Places.longitude,
            round_=round_
        ).label(label)

    @staticmethod
    def get_column_nearest_place_to(label: str, *places: "Places", round_: int=3) -> tuple[Label, Label]:
        """
        AI GENERATED

        Returns two SQL expressions:
        1. Nearest place localisation (name)
        2. Distance to that nearest place

        :param label: Name of those columns.
        :param places: One or more Places instances
        :param round_: Round to [round_] digit after '.'
        """
        if not places:
            raise ValueError("At least one reference place must be provided")

        # Compute distance for each place and store as (distance_expr, place_name)
        distances = [
            (Places.sql_distance(
                lat1=p.latitude,
                lon1=p.longitude,
                lat2=Places.latitude,
                lon2=Places.longitude,
                round_=round_,
            ), p.localisation)
            for p in places
        ]

        # Nearest distance using CASE: select the smallest distance manually
        nearest_distance = distances[0][0]
        for dist_expr, _ in distances[1:]:
            nearest_distance = case(
                (dist_expr < nearest_distance, dist_expr),
                else_=nearest_distance
            )

        nearest_distance = nearest_distance.label(f"{label} (KM)")

        # Nearest place: match the smallest distance
        nearest_place_case = case(
            *((dist_expr == nearest_distance, name) for dist_expr, name in distances),
            else_=None
        ).label(f"{label} (Place)")

        return nearest_place_case, nearest_distance

    @classmethod
    def get_default_entry(cls, localisation: str | None) -> 'Places':
        """Give a Places object with longitude / latitude = None.
        If localisation is None or "", localisation is replaced with Jobs.DEFAULT_LOCALISATION"""
        return Places(
            localisation=localisation if localisation else Jobs.DEFAULT_LOCALISATION,
            longitude=None,
            latitude=None,
        )

    @classmethod
    def get_job_place(
            cls,
            session: Session,
            localisation: Jobs | str | None = None,
    ) -> "Places | None":

        """Gives a Places object related to a localisation / a Job entry.
        None if there is no associated place. A place object otherwise."""
        default_localisation = cls.get_default_entry(
            localisation.localisation if isinstance(localisation, Jobs) else localisation
        )

        return default_localisation.get_existing_self(
            session,
            include_session=True,
            include_database=True
        )
