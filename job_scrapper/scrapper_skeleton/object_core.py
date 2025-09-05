import time
from typing import Sequence

from .logger_core import CoreLogger


# pylint: disable=R0902
# This is the amount of  instance attributes that I need
# pylint: disable=R0913
# This is the amount of argument that I need to initialise attributes
# pylint: disable=R0917
# This is the amount of argument that I need to initialise attributes
class ScrapperObjectCore(CoreLogger):
    """
    Basis of JobScrapperSkeleton. Define all attributes, getters, setters and methods to export
    this object.
    """

    def __init__(
        self,
        title: str,
        localisation: str | None,
        url: str,
        contract_type: str | None,
        field: str | None,
        **metadata,
    ):

        self.field = field
        self.contract_type = contract_type
        self.url = url
        self.localisation = localisation
        self.title = title
        self._fetch_date = time.localtime()
        self._metadata = metadata

        self._distances: dict[str, float] = {}
        self._keywords: dict[str, int] = {}

        # --- --- --- --- Export managements --- --- --- ----

    default_header = [
        "#Fetch Time",
        "Origin",
        "Localisation",
        "Field",
        "Contract",
        "Title",
        "Metadata",
        "Url",
    ]

    def flat(self, sep="\t", with_header=True) -> str:
        """
        Transform an offer to a line inside a flatfile.
        Since the header can vary due to configuration differences, you
            can choose if you want to get the header.

        :param str sep: a separator for the flat file ("\t", ",", ";", ...) Do not use "|" or "=" .
        :param bool with_header: Do the first line contain the header of this offer.
            Behind the scenes, the header is generated even with with_header=False. Due
            to this, with_header=False does not really improve method's speed.
        """
        metadata = []
        for pairs in self._metadata.items():
            metadata.append("=".join(pairs))

        items = [
            time.strftime("%Y-%m-%d %H:%M:%S", self._fetch_date),
            self.__class__.__name__,
            self.localisation,
            self.field,
            self.contract_type,
            self.title,
            "|".join(metadata),
            self.url,
        ]

        header = [*self.default_header]

        for keywords, occurrences in self._keywords.items():
            header.append(keywords + " (#)")
            items.append(str(occurrences))

        for places, distances in self._distances.items():
            header.append(places + " (km)")
            items.append(str(distances))

        str_items = sep.join(items)
        str_header = sep.join(header)

        if with_header:
            return f"{str_header}\n{str_items}"
        return str_items

    @classmethod
    def quick_display_list_of_offers(
        cls, job_list: Sequence["ScrapperObjectCore"]
    ):
        """Quickly display in terminal all jobs from a list of jobs."""
        for i, job in enumerate(job_list):
            if i == 0:
                print(job.flat())
            else:
                print(job.flat(with_header=False))

    # --- --- --- --- Export managements --- --- --- ----
    # --- --- --- --- Attributes managements --- --- --- ----
    @staticmethod
    def clean_string(string: str | None) -> str | None:
        """
        Clean a string by stripping it, replacing every "\t" and "\n" by " " and by
        removing consecutive spaces. Spacing are replaced by "_".
        :param string: A string that should be cleaned
        :return str: The new string
        """
        if string is None:
            return None

        string = string.strip()
        string = string.replace("\n", " ").replace("\t", " ")

        while "  " in string:
            string = string.replace("  ", " ")
        return string.strip().title()

    # --- --- title --- ----
    @property
    def title(self) -> str:
        """Returns the title of this job"""
        return str(self._title)

    @title.setter
    def title(self, value: str | None):
        """Set the title of this job"""
        self._title = self.clean_string(value)

    # --- --- localisation --- ----
    @property
    def localisation(self) -> str:
        """Returns the location of this job"""
        return str(self._localisation)

    @localisation.setter
    def localisation(self, value: str | None):
        """Set the localisation of this job. Use an addresses or
        a geographic landmark"""
        self._localisation = self.clean_string(value)

    # --- --- url --- ----
    @property
    def url(self) -> str:
        """Returns the url that contain more details on this offer"""
        return str(self._url)

    @url.setter
    def url(self, value: str):
        """Set the url that contain more details on this offer"""
        self._url = self.clean_string(value)

    # --- --- contract_type --- ----
    @property
    def contract_type(self) -> str:
        """Returns the contract type (CDI, CDD, Internship...)"""
        return str(self._contract_type).upper()

    @contract_type.setter
    def contract_type(self, value: str | None):
        """Set the contract type (CDI, CDD, Internship...)"""
        self._contract_type = self.clean_string(value)

    # --- --- contract_type --- ----
    @property
    def field(self) -> str:
        """Returns the field of this offer (Bioinformatics, biology, management...)"""
        return str(self._field)

    @field.setter
    def field(self, value: str | None):
        """Set the field of this offer (Bioinformatics, biology, management...)"""
        self._field = self.clean_string(value)

    # --- --- metadata --- ----
    @property
    def metadata(self) -> dict[str, str]:
        """Returns a copy of all metadata"""
        return self._metadata.copy()

    # --- --- fetch_date --- ----
    @property
    def fetch_date(self) -> time.struct_time:
        """Returns a time.struct_time theoretically generated when the job was fetched"""
        return self._fetch_date

    @fetch_date.setter
    def fetch_date(self, timing: time.struct_time):
        """Returns a time.struct_time theoretically generated when the job was fetched"""
        self._fetch_date = timing

    # --- --- distances --- ----
    @property
    def distances(self) -> dict[str, float]:
        """Returns a dictionary with places as key
        and, as value, the distance that separate this job from
        this places"""
        return self._distances.copy()

    # --- --- keywords --- ----
    @property
    def keywords(self) -> dict[str, int]:
        """A dictionary with keywords as ket and integers
        as key. Each value is the number of occurrences inside
        this offer of a key."""
        return self._keywords.copy()

    # --- --- --- --- Attributes managements --- --- --- ----
