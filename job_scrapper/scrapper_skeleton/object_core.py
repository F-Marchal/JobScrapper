import os.path
import time
from typing import Sequence

from tools.logger_core import CoreLogger
import unicodedata
import re
from tools.get_unique_path import get_unique_path

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
    This class represent a job offer and define basic way to export them.
    """

    _workdir = "./JobScrapperWorkDir/"
    
    # Default header is used both for flat file, display and sql main table.
    default_header: dict[str, str] = {
        "#Time_Stamp": "DATE",
        "Origin": "TEXT",
        "Localisation": "TEXT",
        "Field": "TEXT",
        "Contract": "TEXT",
        "Title": "TEXT",
        # "Metadata": "TEXT",
        "Url": "TEXT PRIMARY KEY",
    }
    
    distance_suffix = " (km)"
    keyword_suffix = " (#)"
    time_stamp_suffix = " (date)"
    metadata_suffix = " (met)"
    init_time_stamp_name = "Last sighting" # Should be a clean_string() output.


    @classmethod
    def set_workdir(cls, path: str):
        cls._workdir = path

    @classmethod
    def get_workdir(cls):
        if not os.path.exists(cls._workdir):
            os.makedirs(cls._workdir, exist_ok=True)

        return cls._workdir


    def __init__(
        self,
        url: str,
        title: str | None = None,
        localisation: str | None = None,
        contract_type: str | None = None,
        field: str | None = None,
        **metadata,
    ):
        self.url = url
        self.title = title
        self.localisation = localisation
        self.contract_type = contract_type
        self.field = field
        self._metadata: dict[str, str] = {}
        self._distances: dict[str, float] = {}
        self._keywords: dict[str, int] = {}
        self._time_stamps: dict[str, time.struct_time] = {}

        for key, value in metadata.items():
            self.add_metadata(key, value)
        self.add_time_stamps(self.init_time_stamp_name, self.now())

    # --- --- --- --- Export managements --- --- ---

    def to_dict(self) -> dict[str, str | int | float]:
        """
        :return dict: A dictionary that represent this object. keywords and localisations
        are directly contained inside the dictionary.
        """
        # ---- Default dict ----
        items: list[str | int | float] = [
            self.strftime(
                self._time_stamps[self.init_time_stamp_name]
            ),
            self.get_class_name(),
            self.localisation,
            self.field,
            self.contract_type,
            self.title,
            self.url,
        ]

        header = [*self.default_header]
        # ---- Default dict ----

        # ---- Variable dict ----
        metadata = []
        for pairs in self._metadata.items():
            metadata.append("=".join([str(items) for items in pairs]))

        if metadata:
            header.append("Metadata")
            items.append("|".join(metadata))

        for keywords, occurrences in self._keywords.items():
            header.append(keywords + self.keyword_suffix)
            items.append(occurrences)

        for places, distances in self._distances.items():
            header.append(places + self.distance_suffix)
            items.append(distances)

        for instant_name, time_struct in self._time_stamps.items():
            if instant_name == self.init_time_stamp_name:
                continue

            parsed_time = self.strftime(
                time_struct
            )
            header.append(f"{instant_name}{self.time_stamp_suffix}")
            items.append(str(parsed_time))

        # ---- Variable dict ----
        return dict(zip(header, items))

    @classmethod
    def unflat(cls, header: str, line: str, sep: str = "\t") -> 'ScrapperObjectCore':
        """
        Recreate an object using the output of .flat()
        """
        split_header = header.split(sep)
        split_line = line.split(sep)
        list_default_header = list(cls.default_header)

        unflat = cls("tmp")

        for column_index, column_name in enumerate(split_header):
            column_name = column_name.strip("\n")
            column_value = split_line[column_index].strip("\n")

            if column_name in cls.default_header:
                default_index = list_default_header.index(column_name)

                if default_index == 0:
                    unflat.add_time_stamps(cls.init_time_stamp_name, cls.unstrftime(column_value))

                elif default_index == 1:
                    continue
                elif default_index == 2:
                    unflat.localisation = column_value
                elif default_index == 3:
                    unflat.field = column_value
                elif default_index == 4:
                    unflat.contract_type = column_value
                elif default_index == 5:
                    unflat.title = column_value
                elif default_index == 6:
                    unflat.url = column_value

            elif column_name == "Metadata":
                for pairs in column_value.split("|"):
                    name, value = pairs.split("=")
                    unflat.add_metadata(name, value)

            elif column_name[-len(cls.distance_suffix):] == cls.distance_suffix:
                unflat.add_distance_to(column_name, float(column_value))

            elif column_name[-len(cls.keyword_suffix):] == cls.keyword_suffix:
                unflat.add_keyword_count(column_name, int(column_value))

            elif column_name[-len(cls.time_stamp_suffix):] == cls.time_stamp_suffix:
                unflat.add_time_stamps(column_name, cls.unstrftime(column_value))

        return unflat

    def flat(self, sep: str="\t", with_header: bool=True) -> str:
        """
        Transform an offer to a line inside a flatfile.
        Since the header can vary due to configuration differences, you
            can choose if you want to get the header.

        :param str sep: a separator for the flat file ("\t", ",", ";", ...) Do not use "|" or "=" .
        :param bool with_header: Do the first line contain the header of this offer.
        """
        self_dict = self.to_dict()
        str_items = sep.join([str(item) for item in self_dict.values()])

        if with_header:
            str_header = sep.join(self_dict.keys())
            return f"{str_header}\n{str_items}"
        return str_items

    @classmethod
    def _list_to_flat_file(
        cls, jobs: Sequence["ScrapperObjectCore"], sep: str = "\t",
    ):
        """
        turn a list of jobs to a generator. This generator output the content of .job file.

        When jobs have different headers, the header will be displayed again :
        ```
        #Time_Stamp         Origin Localisation Field    Contract Title Url      Metadata
        2025-09-29 11:45:12 CHU    Paris        Biology  CDD      Title https... A=1|B=2
        2025-09-29 11:45:12 INRAE  Montpellier  Biology  CDI      Title https... A=41|B=20

        #Time_Stamp         Origin Localisation Field    Contract Title Url      Informatic (#) Paris, France (km)
        2025-09-29 11:45:12 CHU   Montpellier  Biology  CDI      Title https... 15             748
        ```
        :param ScrapperObjectCore jobs: A list of ScrapperObjectCore
        :param str sep: Column delimiter. Do not use "|"
        """
        if sep == "|":
            raise ValueError("'|' is not supported as <sep>.")

        last_header = None
        for job_object in jobs:
            header, line = job_object.flat(sep=sep).split("\n")

            if last_header != header:
                yield "\n" + header + "\n"
                last_header = header
            yield line + "\n"

    @classmethod
    def export_to_flat_file(
        cls,
        jobs: Sequence["ScrapperObjectCore"],
        file_path: str | None = None,
        sep: str = "\t",
    ):
        """
        Export a list of job inside a jobfile by .
        When jobs have different headers, the header will be displayed again :
        ```
        #Time_Stamp         Origin Localisation Field    Contract Title Url      Metadata
        2025-09-29 11:45:12 CHU    Paris        Biology  CDD      Title https... A=1|B=2
        2025-09-29 11:45:12 INRAE  Montpellier  Biology  CDI      Title https... A=41|B=20

        #Time_Stamp         Origin Localisation Field    Contract Title Url      Informatic (#) Paris, France (km)
        2025-09-29 11:45:12 CHU   Montpellier  Biology  CDI      Title https... 15             748
        ```

        :param str file_path: A file in which all will be written
        :param ScrapperObjectCore jobs: A list of ScrapperObjectCore
        :param str sep: Column delimiter. Do not use "|"
        """
        if file_path is None:
            file_path = os.path.join(cls.get_workdir(), "JobFiles.job")

        cls.logger.debug("Exporting %s jobs to %s", len(jobs), file_path)

        with open(file_path, "w", encoding="utf-8") as f:
            for lines in cls._list_to_flat_file(jobs, sep=sep):
                f.write(lines)

    @classmethod
    def import_from_flat_file(
            cls,
            file_path: str | None = None,
            sep: str = "\t",
        ):
        if file_path is None:
            file_path = os.path.join(cls.get_workdir(), "JobFiles.job")

        cls.logger.debug(f"Loading jobs from {file_path}")

        with open(file_path, "r", encoding="utf-8") as flux:
            last_header = None
            for lines in flux:
                if not lines.strip():
                    continue

                if lines[0] == "#":
                    last_header = lines
                    continue
                elif not last_header:
                    continue

                obj = cls.unflat(last_header, lines, sep=sep)
                obj.flat(with_header=False)
                yield obj

    @classmethod
    def complete_display_list_of_offers(
        cls, jobs: Sequence["ScrapperObjectCore"], sep: str = "\t"
    ):
        """
        print a list of job inside the terminal as if it was a jobfile.
        :param list[ScrapperObjectCore] jobs: A list of ScrapperObjectCore
        :param str sep: Column delimiter. Do not use "|".
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
    def now():
        """Wrapper for time.localtime()"""
        return time.localtime()

    @staticmethod
    def strftime(instant: time.struct_time) -> str:
        """Wrapper for time.strftime ("%Y-%m-%d %H%M:%S")"""
        return time.strftime(
            "%Y-%m-%d %H:%M:%S", instant
        )

    @staticmethod
    def unstrftime(date_str: str) -> time.struct_time:
        """Inverse of strftime ("%Y-%m-%d %H:%M:%S")"""
        return time.strptime(date_str, "%Y-%m-%d %H:%M:%S")

    # --- --- --- --- Export managements --- --- ---
    # --- --- --- --- Utils --- --- ---

    get_unique_path =  staticmethod(get_unique_path)

    # --- --- --- --- Utils --- --- ---
    # --- --- --- --- Attributes managements --- --- --- ----
    @classmethod
    def clean_string(cls, string: str | None, keep_suffix: bool=False) -> str | None:
        """
        Clean a string to make it safe to use as filename.
        - Transform \s cars to spaces
        - Replace accented characters with unaccented versions
        - Remove invalid filename characters
        - Replace underscores with spaces
        - Remove consecutive spaces
        - Remove suffixes defined in this class

        :param string: A string that should be cleaned
        :param keep_suffix: if True, suffixes wil not be trim out of the string.
        :return str: The cleaned and filename-safe string
        """
        if string is None:
            return ""

        # Ensure that no suffix are allowed at the end of the string.
        # suffixes are test to pass clean_string(keep_suffix=False)
        if not keep_suffix:
            suffix_pattern = (
                f"({re.escape(cls.keyword_suffix)}|"
                f"{re.escape(cls.distance_suffix)}|"
                f"{re.escape(cls.metadata_suffix)}|"
                f"{re.escape(cls.time_stamp_suffix)})$"
            )

            while re.search(suffix_pattern, string):
                string = re.sub(suffix_pattern, "", string).strip().strip('_')

        # replace è, ê, è, ô... by e, o...
        string = unicodedata.normalize('NFD', string)
        string = string.encode('ascii', 'ignore').decode('utf-8')

        # remove cars that can not be contained inside file name,
        # blanc spaces, consecutive underscores and consecutive spaces
        string = re.sub(r'[<>:"/\\|?*]', '', string)
        string = re.sub(r'\s+', '_', string)
        string = re.sub(r'_+', '_', string)
        string = string.strip('_')

        return string.replace("_", " ").capitalize()

    @classmethod
    def is_a_cleaned_string(cls, string: str | None) -> bool:
        return  cls.clean_string(string) == string

    def __eq__(self, other):
        """Strict equality between two ScrapperObjectCore"""
        if not isinstance(other, ScrapperObjectCore):
            return NotImplemented

        return (
            self.url == other.url
            and self.title == other.title
            and self.localisation == other.localisation
            and self.contract_type == other.contract_type
            and self.field == other.field
            and self._metadata == other._metadata
            and self._distances == other._distances
            and self._keywords == other._keywords
            and self.compare_two_time_stamps_dict(self._time_stamps, other._time_stamps)
        )

    def __ne__(self, other):
        """Strict inequality between two ScrapperObjectCore"""
        eq = self.__eq__(other)
        if eq is NotImplemented:
            return NotImplemented
        return not eq

    @staticmethod
    def compare_two_time_stamps(t1: time.struct_time, t2: time.struct_time) -> bool:
        """Does two time stamp are equals ? (do not take into account tm_isdst)"""
        if t1.tm_isdst == t2.tm_isdst:
            return t1 == t2

        if t2.tm_isdst != -1:
            t2 = time.struct_time((
                t2.tm_year, t2.tm_mon, t2.tm_mday,
                t2.tm_hour, t2.tm_min, t2.tm_sec,
                t2.tm_wday, t2.tm_yday, t1.tm_isdst  # tm_isdst
            ))

        return t1 == t2

    @classmethod
    def compare_two_time_stamps_dict(
            cls,
            d1: dict[str, time.struct_time],
            d2: dict[str, time.struct_time]
    ) -> bool:
        """Does two ScrapperObjectCore's time stamps dict are equal.
         Uses compare_two_time_stamps to compare time stamps"""
        if d1.keys() != d2.keys():
            return False

        keys = list(d1.keys())
        i = 0
        equal_time_stamps = True
        while equal_time_stamps and i < len(keys):
            key = keys[i]
            if not cls.compare_two_time_stamps(d1[key], d2[key]):
                equal_time_stamps = False
            i += 1

        return equal_time_stamps


    def equivalent_to(self, other: 'ScrapperObjectCore') -> bool:
        """Returns true when other have the same url as self"""
        return self.url == other.url

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
        return str(self._localisation).title()

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

    def add_metadata(self, name: str, value: str):
        """Add an entry inside this job metadata
        :param name: Will be passed inside clean_string
        :param value: Can not contain any pipe '|', any \s will be replaced by _"""
        if "|" in value:
            raise ValueError("No pipe ('|') allowed as metadata value.")

        name = self.clean_string(name)
        value = re.sub(r'\s+', '_', value)
        value = re.sub(r'_+', '_', value)

        self._metadata[name] = value

    def remove_metadata(self, name: str):
        """Delete a metadata attached to this job offer."""
        name = self.clean_string(name)
        if name in self._metadata:
            del self._metadata[name]

    def retrieve_metadata(self, name: str) -> str:
        """Retrieve an entry inside this job metadata"""
        name = self.clean_string(name)
        return self._metadata[name]


    def metadata_exist(self, name: str) -> bool:
        """Says if a metadata with the same <name> is defined in <self.metadata>"""
        return self.clean_string(name) in self._metadata

    # --- --- time_stamps --- ----
    @property
    def time_stamps(self) -> dict[str, time.struct_time]:
        """Returns a dictionary that contained one or multiple time stamp."""
        return self._time_stamps.copy()

    def add_time_stamps(self, name: str, value: time.struct_time):
        """Add an entry inside this job time stamps
        If <name> contains <self.time_stamp_suffix> as suffix it will be removed"""
        name = self.clean_string(name)
        self._time_stamps[name] = value

    def remove_time_stamps(self, name: str):
        """Delete a time stamp from the list of known time stamps."""
        name = self.clean_string(name)

        if name == self.init_time_stamp_name:
            raise ValueError(f"'{self.init_time_stamp_name}' can not be removed from time stamps !")

        elif name in self._time_stamps:
            del self._time_stamps[name]

    def retrieve_time_stamps(self, name: str) -> time.struct_time:
        """Retrieve an entry inside this job time stamps
        If <name> contains <self.time_stamp_suffix> as suffix it will be removed"""
        name = self.clean_string(name)
        return self._time_stamps[name]

    def time_stamps_exist(self, name: str) -> bool:
        """Says if a time stamp with the same <name> is defined in <self.time_stamps>
        If <name> contains <self.time_stamp_suffix> as suffix it will be removed"""
        return self.clean_string(name) in self._time_stamps

    # --- --- distances --- ----
    @property
    def distances(self) -> dict[str, float]:
        """Returns a dictionary with places as key
        and, as value, the distance that separate this job from
        this places"""
        return self._distances.copy()

    def add_distance_to(self, place: str, distance: float):
        """Add a distances that separate this offer from a <place>.
         If <place> contains <self.distance_suffix> as suffix it will be removed"""
        place = self.clean_string(place)
        self._distances[place] = float(distance)

    def remove_distance_to(self, place: str):
        """Delete a place from the list known places in the distance dictionary."""
        place = self.clean_string(place)
        if place in self._distances:
            del self._distances[place]

    def retrieve_distance_to(self, place: str) -> float:
        """Retrieves distances that separate this offer from a <place>.
         If <place> contains <self.distance_suffix> as suffix it will be removed"""
        place = self.clean_string(place)
        return self._distances[place]

    def distance_to_exist(self, place: str, default_value_do_not_count: bool=True) -> bool:
        """Says if the distance that separate self.localisation and a <place>
        is defined in <self._distances>
         If <place> contains <self.distance_suffix> as suffix it will be removed"""
        place = self.clean_string(place)
        if default_value_do_not_count:
            return place in self._distances and self._distances[place] != -1
        return place in self._distances

    # --- --- keywords --- ----
    @property
    def keywords(self) -> dict[str, int]:
        """Returns a dictionary with keywords as ket and integers
        as key. Each value is the number of occurrences inside
        this offer of a key."""
        return self._keywords.copy()

    def add_keyword_count(self, keyword: str, count: int):
        """Add the number or occurrences of a keyword in job offer
         If <keyword> contains <self.keyword_suffix> as suffix it will be removed"""
        keyword = self.clean_string(keyword)
        self._keywords[keyword] = int(count)

    def remove_keyword_count(self, keyword: str):
        """Delete keyword from the list of known keywords attached to this job offer."""
        keyword = self.clean_string(keyword)
        if keyword in self._keywords:
            del self._keywords[keyword]

    def retrieve_keyword_count(self, keyword: str) -> int:
        """Retrieve the number or occurrences of a keyword in job offer
         If <keyword> contains <self.keyword_suffix> as suffix it will be removed"""
        keyword = self.clean_string(keyword)
        return self._keywords[keyword]

    def keyword_exist(self, keyword: str, default_value_do_not_count: bool=True) -> bool:
        """Says if the number of occurrence contained in this offer is known.
        If <keyword> contains <self.keyword_suffix> as suffix it will be removed"""
        keyword = self.clean_string(keyword)
        if default_value_do_not_count:
            return keyword in self._keywords and self._keywords[keyword] != -1
        return keyword in self._keywords

    # --- --- --- --- Attributes managements --- --- --- ----


if __name__ == "__main__":
    pass
