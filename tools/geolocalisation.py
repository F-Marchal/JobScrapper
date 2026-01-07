from keyword import kwlist
from logging import Logger

from geopy.distance import geodesic  # type: ignore[import-untyped]
from geopy.exc import GeopyError  # type: ignore[import-untyped]
from geopy.extra.rate_limiter import RateLimiter  # type: ignore[import-untyped]
from geopy.geocoders import Nominatim  # type: ignore[import-untyped]
from geopy.location import Location  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from sql.tables.places.distances import Distances
from sql.tables.places.places import Places
import re
from unidecode import unidecode

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
            "swallow_exceptions" : True,
        """
        rl_kw = {
            "min_delay_seconds": 3,
            "max_retries": 3,
            "error_wait_seconds": 30,
            "swallow_exceptions": True,
        }
        rl_kw.update(rate_limiter_kw)

        self.logger: Logger | None = logger
        self._geolocator: Nominatim = Nominatim(
            user_agent=contact,
            timeout=timeout,
        )
        self._rate_limiter: RateLimiter = RateLimiter(
            self._geolocator.geocode, **rl_kw
        )
        self._contact = contact

    #  --- --- Main methods --- ---
    def geolocate(
        self,
        session: Session,
        place: str,
        lazy: bool = True,
        add_in_database: bool = True,
        restrict_country_codes: list[str | None] | None = None,
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
        :param str restrict_country_codes: An optional list of country code.
            If geopy can not find a place using the first country code,
            the next one is used and so on. If not filled, no country code is used.
            Use 'None' in the list make a request without any country code.
        """
        existing_entry = self.get_localisation_from_database(session, place)

        if existing_entry and lazy:
            return existing_entry.lat, existing_entry.long

        if restrict_country_codes is None:
            restrict_country_codes = [None]

        lat, long = None, None
        i = 0
        while i < len(restrict_country_codes) and (lat, long) == (None, None):
            code = restrict_country_codes[i]
            if code:
                lat, long = self.request(place, country_codes=code)
            else:
                lat, long = self.request(place)
            i += 1

        if add_in_database:
            session.add(
                Places(localisation=place, longitude=long, latitude=lat)
            )

        return lat, long

    def _request(self, place: str, *args, **kwargs) -> Location | None:
        """Run the RateLimiter and returns the result"""
        return self._rate_limiter(place, *args, **kwargs)

    def request(self, place: str, *args, **kwargs) -> tuple[float | None, float | None]:
        """
        Request the coordinate of a place.
        :param place: The name of a place
        :return:
        """
        norm_place = self.clean_place_name(place)
        try:
            # Try to run call geopy and to return the result.
            if self.logger:
                self.logger.info(
                    "Searching coordinates of '%s' (normalised as '%s') using '%s' ('%s') with"
                    "\nargs=%s"
                    "\nkwargs=%s",
                    place,
                    norm_place,
                    self._geolocator,
                    self._contact,
                    args,
                    kwargs
                )
            localisation: Location | None = self._request(norm_place, *args, **kwargs)
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
    @classmethod
    def compute_distance(
        cls,
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
        existing_distance = cls.get_distances_from_database(
            session, reference_localisation, second_localisation
        )

        if existing_distance and lazy:
            return float(getattr(existing_distance, "distance"))

        ref_entry = cls.get_localisation_from_database(
            session, reference_localisation
        )
        sec_entry = cls.get_localisation_from_database(
            session, second_localisation
        )

        if not isinstance(ref_entry, Places):
            return None
        if not isinstance(sec_entry, Places):
            return None
        if not cls._compute_distance_valid_couple(ref_entry, sec_entry):
            return None

        geo = geodesic(ref_entry.coord, sec_entry.coord)

        if add_in_database:
            session.add(
                Distances(
                    reference_localisation=reference_localisation,
                    job_localisation=second_localisation,
                    distance=geo.km,
                )
            )

        if isinstance(geo, Places):
            return geodesic(ref_entry.coord, sec_entry.coord).km
        return geo.km

    @classmethod
    def _compute_distance_valid_couple(
        cls, ref_entry: Places, sec_entry: Places, logger: Logger | None = None,
    ) -> bool:
        """
        Test if ref_entry and sec_entry can be used to compute
        a distance. Returns True if True, False otherwise.
        """

        if not ref_entry:
            if logger:
                logger.warning(
                    "Can not Process coordinates of '%s' : Unknown place.",
                    ref_entry,
                )
            return False

        if not sec_entry:
            if logger:
                logger.warning(
                    "Can not Process coordinates of '%s' : Unknown place.",
                    sec_entry,
                )
            return False

        if not ref_entry.is_computable():
            if logger:
                logger.warning(
                    "Can not Process coordinates of '%s'. Unknown coordinate.",
                    ref_entry.localisation,
                )
            return False
        if not sec_entry.is_computable():
            if logger:
                logger.warning(
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

    ABBREVIATIONS = {
        r"\bst\b": "saint",
        r"\bste\b": "sainte"
    }

    @classmethod
    def expand_abbreviations(cls, text: str) -> str:
        for pattern, repl in cls.ABBREVIATIONS.items():
            text = re.sub(pattern, repl, text)
        return text

    @classmethod
    def remove_cedex(cls, text): # AI Generated
        return re.sub(r"\bcedex\b(\s*\d+)?", "", text).strip()

    @classmethod
    def format_arrondissement(cls, text: str) -> str:  # AI Generated
        text = text.strip()
        # Only Paris / Lyon / have arrondissement
        match = re.match(r"^(paris|lyon|marseille)\s*(\d{1,2})$", text, re.IGNORECASE)

        if match:
            city = match.group(1).capitalize()
            num = int(match.group(2))  # Remove starting 0
            return f"{city} {num}e arrondissement, France"
        return text

    @staticmethod
    def normalize_place_name(text: str) -> str:  # AI Generated
        text = text.lower().strip()

        # Remove accents
        text = unidecode(text)

        # Remove parenthesis en everything within
        text = re.sub(r"\([^)]*\)", " ", text)


        # Remove ", ' . / : ; ! ? ..."
        text = re.sub(r"[^\w\s-]", " ", text)

        # Standardise spacingg
        text = re.sub(r"\s+", " ", text)

        return text

    @classmethod
    def clean_place_name(cls, text: str) -> str:  # AI Generated
        text = cls.normalize_place_name(text)
        text = cls.expand_abbreviations(text)
        text = cls.remove_cedex(text)
        text = cls.format_arrondissement(text)
        return text


    #  --- --- Tools --- ---
