from geopy.distance import geodesic  # type: ignore[import-untyped]
from geopy.geocoders import Nominatim  # type: ignore[import-untyped]
from geopy.location import Location
from sql.tables.places.places import Places
from sql.tables.places.distances import Distances
from sqlalchemy.orm import Session
from logging import Logger
from geopy.extra.rate_limiter import RateLimiter


class Geolocalisation:
    def __init__(
            self,
            contact: str,
            logger: Logger | None = None,
            timeout: int = 60,
            **rate_limiter_kw,
    ):
        rl_kw = {
            "min_delay_seconds" : 2,
            "max_retries" : 3,
            "error_wait_seconds" : 30,
            "swallow_exceptions" : False,
        }
        rl_kw.update(rate_limiter_kw)
        self.timeout = timeout
        self.logger = logger
        self._geolocator = Nominatim(user_agent=contact)
        self._rate_limiter = RateLimiter(
            self._geolocator.geocode,
            **rl_kw
        )

    def geolocate(
            self,
            session: Session,
            place: str,
            lazy: bool = True,
            add_in_database: bool = True
    ) -> tuple[float | None, float | None]:
        existing_entry = self.get_localisation_from_database(session, place)

        if existing_entry and lazy:
            return existing_entry.latitude, existing_entry.longitude

        lat, long = self.request(place)

        if add_in_database:
            session.add(
                Places(
                    localisation=place,
                    longitude=long,
                    latitude=lat
                )
            )

        return lat, long

    def _request(self, place: str) -> Location | None:
        return self._rate_limiter(place)

    def request(self, place: str)-> tuple[float | None, float | None]:
        try:
            localisation: Location | None = self._request(place)
            if localisation is None:
                return None, None
            return float(localisation.latitude), float(localisation.longitude)

        except Exception as err:
            if self.logger: self.logger.error(
                "An error occurred during geolocalisation of '%s'."
                "\nrate_limiter=%s"
                "\ngeolocator=%s"
                "\nError : %s",
                place, self._rate_limiter, self._geolocator, err
            )
        return None, None

    def get_localisation_from_database(
            self,
            session: Session,
            localisation: str
    ):
        default_localisation = Places(
            localisation=localisation,
            longitude=None,
            latitude=None
        )
        return default_localisation.get_existing_self(
            session,
            include_session=True,
            include_database=True
        )

    def get_distances_from_database(
            self,
            session: Session,
            reference_localisation: str,
            second_localisation: str,
    ):

        default_distance = Distances(
            reference_localisation=reference_localisation,
            second_localisation=second_localisation,
            distance=None
        )
        return default_distance.get_existing_self(
            session,
            include_session=True,
            include_database=True
        )

    def compute_distance(
            self,
            session: Session,
            reference_localisation: str,
            second_localisation: str,
            lazy: bool = True,

    ) -> float | None:
        existing_distance = self.get_distances_from_database(
            session,
            reference_localisation,
            second_localisation
        )

        if existing_distance and lazy:
            return existing_distance.distance

        ref_entry = self.get_localisation_from_database(session, reference_localisation)
        sec_entry = self.get_localisation_from_database(session, second_localisation)

        if not ref_entry.is_computable():
            if self.logger: self.logger.warning(
                "Can not Process coordinates of '%s'.", ref_entry.localisation
            )
            return None
        if not sec_entry.is_computable():
            if self.logger: self.logger.warning(
                "Can not Process coordinates of '%s'.", ref_entry.localisation
            )
            return None

        geo =  geodesic(ref_entry.coord, sec_entry.coord)
        if geo:
            return geodesic(ref_entry.coord, sec_entry.coord).km
        return None

