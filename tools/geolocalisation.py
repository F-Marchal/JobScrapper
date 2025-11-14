from logging import Logger

from geopy.distance import geodesic  # type: ignore[import-untyped]
from geopy.exc import GeopyError  # type: ignore[import-untyped]
from geopy.extra.rate_limiter import RateLimiter  # type: ignore[import-untyped]
from geopy.geocoders import Nominatim  # type: ignore[import-untyped]
from geopy.location import Location  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from sql.tables.places.distances import Distances
from sql.tables.places.places import Places


class Geolocalisation:
    """Simple too class that wrap some geopy methods and adapt
    them to JobScrapper."""

    def __init__(
        self,
        contact: str,
        logger: Logger | None = None,
        timeout: int = 60,
        **rate_limiter_kw,
    ):
        """
        :param str contact: A way to contact the person that uses the program.
            (Compliance with Geopy services)
        :param logger: An optional logger to display errors and information.
        :param timeout: How long a request can be
        :param rate_limiter_kw: Configuration for a RateLimiter : Default :
            "min_delay_seconds" : 2,
            "max_retries" : 3,
            "error_wait_seconds" : 30,
            "swallow_exceptions" : False,
        """
        rl_kw = {
            "min_delay_seconds": 2,
            "max_retries": 3,
            "error_wait_seconds": 30,
            "swallow_exceptions": True,
        }
        rl_kw.update(rate_limiter_kw)

        self.timeout: int = timeout
        self.logger: Logger | None = logger
        self._geolocator: Nominatim = Nominatim(user_agent=contact)
        self._rate_limiter: RateLimiter = RateLimiter(
            self._geolocator.geocode, **rl_kw
        )

    #  --- --- Main methods --- ---
    def geolocate(
        self,
        session: Session,
        place: str,
        lazy: bool = True,
        add_in_database: bool = True,
    ) -> tuple[float | None, float | None]:
        """
        Geolocate a place and returns longitude / latitude.
        If this <place> is known in the database, the value of the database will
        be output.
        :param Session session: A session connected to a database
        :param str place: The name of a localisation
        :param bool lazy: If the place exists in database, geopy is not called.
        :param bool add_in_database:  If True, when geopy is called, the
            result is stored in database
        """
        existing_entry = self.get_localisation_from_database(session, place)

        if existing_entry and lazy:
            return existing_entry.lat, existing_entry.long

        lat, long = self.request(place)

        if add_in_database:
            session.add(
                Places(localisation=place, longitude=long, latitude=lat)
            )

        return lat, long

    def _request(self, place: str) -> Location | None:
        """Run the RateLimiter and returns the result"""
        return self._rate_limiter(place)

    def request(self, place: str) -> tuple[float | None, float | None]:
        """
        Request the coordinate of a place.
        :param place: The name of a place
        :return:
        """
        try:
            # Try to run call geopy and to return the result.
            if self.logger:
                self.logger.debug(
                    "Searching coordinates of '%s' using '%s'.",
                    place,
                    self._geolocator,
                )
            localisation: Location | None = self._request(place)
            if localisation is None:
                return None, None
            return float(localisation.latitude), float(localisation.longitude)

        except GeopyError as err:
            # If it fails, logs the error
            if self.logger:
                self.logger.error(
                    "An error occurred during geolocalisation of '%s'."
                    "\nrate_limiter=%s"
                    "\ngeolocator=%s"
                    "\nError : %s",
                    place,
                    self._rate_limiter,
                    self._geolocator,
                    err,
                )
        return None, None

    # pylint: disable=R0913,R0917
    def compute_distance(
        self,
        session: Session,
        reference_localisation: str,
        second_localisation: str,
        lazy: bool = True,
        add_in_database: bool = True,
    ) -> float | None:
        """
        Returns the distance between two localisation.
        If the distance between those two localisation
        exist in the database, the value from the database
        is returned.

        :param Session session: A session connected to a database
        :param str reference_localisation:  A place of reference
        :param str second_localisation: Another localisation
        :param bool lazy: If this couple of place exists in a Distance
            entry, the distance contained in this entry is returned.
        :param bool add_in_database: If True, when a couple of place
            does not exist in Distance, the entry is added to the database
        """
        # Try to find an equivalent in
        existing_distance = self.get_distances_from_database(
            session, reference_localisation, second_localisation
        )

        if existing_distance and lazy:
            return float(getattr(existing_distance, "distance"))

        ref_entry = self.get_localisation_from_database(
            session, reference_localisation
        )
        sec_entry = self.get_localisation_from_database(
            session, second_localisation
        )

        if not isinstance(ref_entry, Places):
            return None
        if not isinstance(sec_entry, Places):
            return None
        if not self._compute_distance_valid_couple(ref_entry, sec_entry):
            return None

        geo = geodesic(ref_entry.coord, sec_entry.coord)

        if add_in_database:
            session.add(
                Distances(
                    reference_localisation=reference_localisation,
                    second_localisation=second_localisation,
                    distance=geo.km,
                )
            )

        if isinstance(geo, Places):
            return geodesic(ref_entry.coord, sec_entry.coord).km
        return None

    def _compute_distance_valid_couple(
        self, ref_entry: Places, sec_entry: Places
    ) -> bool:
        """
        Test if ref_entry and sec_entry can be used to compute
        a distance. Returns True if True, False otherwise.
        """

        if not ref_entry:
            if self.logger:
                self.logger.warning(
                    "Can not Process coordinates of '%s' : Unknown place.",
                    ref_entry,
                )
            return False

        if not sec_entry:
            if self.logger:
                self.logger.warning(
                    "Can not Process coordinates of '%s' : Unknown place.",
                    sec_entry,
                )
            return False

        if not ref_entry.is_computable():
            if self.logger:
                self.logger.warning(
                    "Can not Process coordinates of '%s'. Unknown coordinate.",
                    ref_entry.localisation,
                )
            return False
        if not sec_entry.is_computable():
            if self.logger:
                self.logger.warning(
                    "Can not Process coordinates of '%s'. Unknown coordinate.",
                    ref_entry.localisation,
                )
            return False
        return True

    #  --- --- Main methods --- ---
    #  --- --- Tools --- ---
    @staticmethod
    def get_localisation_from_database(
        session: Session, localisation: str
    ) -> Places | None:
        """
        Returns a Places entry based on a localisation.
        :param session: Session connected to a database
        :param localisation: The place to find
        """
        # Create a dfault Places entry
        default_localisation = Places(
            localisation=localisation, longitude=None, latitude=None
        )

        # Try to find an equivalent in the database
        existing = default_localisation.get_existing_self(
            session, include_session=True, include_database=True
        )

        return existing

    @staticmethod
    def get_distances_from_database(
        session: Session,
        reference_localisation: str,
        second_localisation: str,
    ) -> Distances | None:
        """
        Returns a Distances entry that represent the distance between to places.
        Returns None if no matching entry exist.
        """

        default_distance = Distances(
            reference_localisation=reference_localisation,
            job_localisation=second_localisation,
            distance=None,
        )
        existing = default_distance.get_existing_self(
            session, include_session=True, include_database=True
        )

        return existing

    #  --- --- Tools --- ---
