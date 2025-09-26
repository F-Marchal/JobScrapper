import os.path
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

    workdir = "./JobScrapperWorkDir/"

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
        self._metadata = metadata

        self._distances: dict[str, float] = {}
        self._keywords: dict[str, int] = {}
        local_time = time.localtime()
        self._time_stamps: dict[str, time.struct_time] = {
            "last_sighting": local_time,
        }

    # --- --- --- --- Export managements --- --- ---
    # Default header is used both for flat file, display and sql main table.
    default_header = {
        "#Time_Stamp": "DATE",
        "Origin": "TEXT",
        "Localisation": "TEXT",
        "Field": "TEXT",
        "Contract": "TEXT",
        "Title": "TEXT",
        # "Metadata": "TEXT",
        "Url": "TEXT PRIMARY KEY",
    }

    def to_dict(self):
        """
        :return dcit: A dictionary that represent this object. keywords and localisations
        are directly contained inside the dictionary.
        """
        items = [
            time.strftime(
                "%Y-%m-%d %H:%M:%S", self._time_stamps["last_sighting"]
            ),
            self.get_class_name(),
            self.localisation,
            self.field,
            self.contract_type,
            self.title,
            self.url,
        ]

        header = [*self.default_header]

        metadata = []
        for pairs in self._metadata.items():
            metadata.append("=".join([str(items) for items in pairs]))

        if metadata:
            header.append("Metadata")
            items.append("|".join(metadata))

        for keywords, occurrences in self._keywords.items():
            header.append(keywords + " (#)")
            items.append(str(occurrences))

        for places, distances in self._distances.items():
            header.append(places + " (km)")
            items.append(str(distances))

        return dict(zip(header, items))

    def flat(self, sep="\t", with_header=True) -> str:
        """
        Transform an offer to a line inside a flatfile.
        Since the header can vary due to configuration differences, you
            can choose if you want to get the header.

        :param str sep: a separator for the flat file ("\t", ",", ";", ...) Do not use "|" or "=" .
        :param bool with_header: Do the first line contain the header of this offer.
        """
        self_dict = self.to_dict()
        str_items = sep.join(self_dict.values())

        if with_header:
            str_header = sep.join(self_dict.keys())
            return f"{str_header}\n{str_items}"
        return str_items

    @classmethod
    def _list_to_flat_file(
        cls, jobs: Sequence["ScrapperObjectCore"], sep: str = "\t"
    ):
        """
        turn a list of jobs to a generator. This generator output the content of .job file.
        :param ScrapperObjectCore jobs: A list of ScrapperObjectCore
        :param str sep: Column delimiter. Do not use "|"
        """
        last_header = None
        for job_object in jobs:
            header, line = job_object.flat(sep=sep).split("\n")

            if last_header != header:
                yield "\n" + header + "\n"
                last_header = header
            yield line + "\n"

    @classmethod
    def list_to_flat_file(
        cls,
        file_path: str | None,
        jobs: Sequence["ScrapperObjectCore"],
        sep: str = "\t",
    ):
        """
        Export a list of job inside a jobfile.
        :param str file_path: A file in which all will be written
        :param ScrapperObjectCore jobs: A list of ScrapperObjectCore
        :param str sep: Column delimiter. Do not use "|"
        """
        cls.logger.debug("Exporting %s jobs to %s", len(jobs), file_path)
        if file_path is None:
            file_path = os.path.join(cls.workdir, "JobFiles")

        with open(file_path, "w", encoding="utf-8") as f:
            for lines in cls._list_to_flat_file(jobs, sep=sep):
                f.write(lines)

    @classmethod
    def complete_display_list_of_offers(
        cls, jobs: Sequence["ScrapperObjectCore"], sep: str = "\t"
    ):
        """
        print a list of job inside the terminal as if it was a jobfile.
        :param list[ScrapperObjectCore] jobs: A list of ScrapperObjectCore
        :param str sep: Column delimiter. Do not use "|"
        :return:
        """
        for lines in cls._list_to_flat_file(jobs, sep=sep):
            print(lines, end="")

    @staticmethod
    def quick_display_list_of_offers(job_list: Sequence["ScrapperObjectCore"]):
        """Quickly display in terminal all jobs from a list of jobs. is printed only one time.
        If the <job_list> has been generated using multiple configurations use <complete_display_list_of_offers>
        """
        for i, job in enumerate(job_list):
            if i == 0:
                print(job.flat())
            else:
                print(job.flat(with_header=False))

    @classmethod
    def get_class_name(cls) -> str:
        """Returns cls.__name__"""
        return cls.__name__

    @staticmethod
    def get_unique_file_name(file_path: str, ext: str) -> str:
        """
        Give a filename that does not exist.
        if <file_path>.<ext> exist, <file_path>-<#>.<ext> will be tested. <#> is incremented
        until an unoccupied file name is found.
        :param str file_path: folder/filename
        :param str ext: file extension that should be added to  folder/filename (-->  folder/filename.ext)
        :return:
        """
        default_name = file_path + "." + ext
        if not os.path.exists(file_path + ext):
            return default_name

        counter = 1
        filename = file_path + "-{}." + ext
        while os.path.isfile(filename.format(counter)):
            counter += 1

        return filename.format(counter)

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
            return ""

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
        self._url = value.strip()

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

    # --- --- time_stamps --- ----
    @property
    def time_stamps(self) -> dict[str, time.struct_time]:
        """Returns a dictionary that contained one or multiple time stamp."""
        return self._time_stamps

    # --- --- distances --- ----
    @property
    def distances(self) -> dict[str, float]:
        """Returns a dictionary with places as key
        and, as value, the distance that separate this job from
        this places"""
        return self._distances

    # --- --- keywords --- ----
    @property
    def keywords(self) -> dict[str, int]:
        """A dictionary with keywords as ket and integers
        as key. Each value is the number of occurrences inside
        this offer of a key."""
        return self._keywords

    # --- --- --- --- Attributes managements --- --- --- ----


if __name__ == "__main__":
    pass
