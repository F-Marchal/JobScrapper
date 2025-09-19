import os.path
import sqlite3
import time
from contextlib import contextmanager
from typing import Sequence

from mypy.types_utils import AnyType

from .logger_core import CoreLogger


# pylint: disable=R0902
# This is the amount of  instance attributes that I need
# pylint: disable=R0913
# This is the amount of argument that I need to initialise attributes
# pylint: disable=R0917
# This is the amount of argument that I need to initialise attributes
# pylint: disable=R0904
# Most of the public methods are setter and getter for my numerous attributes
class ScrapperObjectCore(CoreLogger):
    """
    Basis of JobScrapperSkeleton. Define all attributes, getters, setters and methods to export
    this object.
    """

    database_file_name = "AllJobs"
    main_table_name = "Jobs"
    metadata_table_name = "Metadata"
    keywords_table_name = "KeywordsCount"
    distances_table_name = "Distances"
    time_stamps_table_name = "TimeStamps"

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
        local_time =  time.localtime()
        self._time_stamps: dict[str, time.struct_time] = {
            "last_sighting": local_time,
        }

        # first_sighting
        with self.write_in_database() as cursor:
            cursor.execute(
                """
                select time_stamp from TimeStamps where TimeStamps.url=? and TimeStamps.keyword="first_sighting";
                """,
                [self.url]
            )
            result = cursor.fetchall()

        if result:
            try:
                self._time_stamps["first_sighting"] = time.strptime(result[-1][0], "%Y-%m-%d %H:%M:%S")
            except ValueError as ve:
                self.logger.error("Error during loading of the 'first_sighting' time_stamp of '%s' : \n %s", url, ve)
        else:
            self._time_stamps["first_sighting"] = local_time

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
            time.strftime("%Y-%m-%d %H:%M:%S", self._time_stamps["last_sighting"]),
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
            metadata.append("=".join(pairs))

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
    def list_to_sql(cls, jobs: Sequence["ScrapperObjectCore"]):
        """
        Export a list of job inside the sql database.
        :param list ["ScrapperObjectCore"] jobs: A list of ScrapperObjectCore
        :return:
        """
        cls.logger.debug("Exporting %s jobs to sql database", len(jobs))
        for job_obj in jobs:
            job_obj.sql_export()

    @classmethod
    def get_class_name(cls) -> str:
        """Returns cls.__name__"""
        return cls.__name__

    #  --- --- --- --- Sqlite --- --- --- ----
    # --- --- Names and paths --- ---

    @classmethod
    def get_database_path(cls, workdir: str | None = None):
        """
        :param str workdir: a path to a directory
        :return str: A path that lead to a database file.
        """
        if not workdir:
            workdir = cls.workdir

        return os.path.abspath(
            os.path.join(workdir, cls.database_file_name + ".db")
        )

    @classmethod
    def sql_compatible_header_keyword(cls, keyword: str):
        """
        Transform a string to ensure that a keyword can be used as
        header inside a sql table.
        :param str keyword: a string
        :return:
        """
        return keyword.lower().replace("#", "")

    # --- --- Names and paths --- ---
    # --- --- Databases --- ---
    @classmethod
    def _create_main_sql_table_command(cls) -> str:
        database_definition = [
            f"CREATE TABLE IF NOT EXISTS  {cls.main_table_name} (",
        ]
        for column_name, column_type in cls.default_header.items():
            column_name = cls.sql_compatible_header_keyword(column_name)
            database_definition.append(f"{column_name} {column_type},")
        database_definition[-1] = database_definition[-1].removesuffix(",")

        # Close definition
        database_definition.append(")")

        database_command = "\n".join(database_definition)
        return database_command

    @classmethod
    def _create_metadata_sql_table_command(cls) -> str:
        command = [
            f"CREATE TABLE IF NOT EXISTS {cls.metadata_table_name} (",
            "url TEXT,",
            "key TEXT NOT NULL,",
            "value TEXT NOT NULL,",
            "PRIMARY KEY(url, key),"
            f"FOREIGN KEY (url) REFERENCES {cls.main_table_name}(url)",
            ");",
        ]
        return "\n".join(command)

    @classmethod
    def _create_keywords_sql_table_command(cls) -> str:
        command = [
            f"CREATE TABLE IF NOT EXISTS {cls.keywords_table_name} (",
            "url TEXT KEY,",
            "keyword TEXT NOT NULL,",
            "occurrence INT NOT NULL,",
            "PRIMARY KEY(url, keyword),"
            f"FOREIGN KEY (url) REFERENCES {cls.main_table_name}(url)",
            ");",
        ]
        return "\n".join(command)

    @classmethod
    def _create_distances_sql_table_command(cls) -> str:
        """
        :return str: The command that allow the creation of the distance table.
        """
        return (
            f"CREATE TABLE IF NOT EXISTS {cls.distances_table_name} ("
            + "localisation1 TEXT NOT NULL,"
            + "localisation2 TEXT NOT NULL,"
            + "distance REAL NOT NULL,"
            + "PRIMARY KEY(localisation1, localisation2)"
            ");"
        )

    @classmethod
    def _create_time_stamps_sql_table_command(cls):
        """
        :return str: The command that allow the creation of the time stamps table.
        """
        command = [
            f"CREATE TABLE IF NOT EXISTS {cls.time_stamps_table_name} (",
            "url TEXT KEY,",
            "keyword TEXT NOT NULL,",
            "time_stamp DATE NOT NULL,",
            "PRIMARY KEY(url, keyword),"
            f"FOREIGN KEY (url) REFERENCES {cls.main_table_name}(url)",
            ");",
        ]
        return "\n".join(command)

    @staticmethod
    def sort_localisations(localisation1: str, localisation2: str) -> list[str]:
        """
        Sort two string by alphabetic order.
        :param str localisation1: a string
        :param str localisation2: another string
        :return:
        """
        return sorted([localisation1, localisation2])

    @classmethod
    def ensure_tables_presences(cls, cursor):
        """
        Ensure that all table needed for ScrapperObjectCore exportation
        exist inside the database.
        :param cursor: A sqlite cursor.
        """
        cursor.execute(cls._create_main_sql_table_command())
        cursor.execute(cls._create_metadata_sql_table_command())
        cursor.execute(cls._create_keywords_sql_table_command())
        cursor.execute(cls._create_distances_sql_table_command())
        cursor.execute(cls._create_time_stamps_sql_table_command())

    @classmethod
    @contextmanager
    def write_in_database(cls):
        """
        Made to be used with the <with> statement. Gives a cursor and ensure
        that :
        - All databases exists
        - The cursor is closed
        - The command are commited.
        ```
        with self.write_in_database() as cursor:
            cursor.execute(true_command)
        ```
        """
        data_path = cls.get_database_path()
        data_dir = os.path.dirname(data_path)
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        conn = sqlite3.connect(data_path)
        cursor = conn.cursor()
        cls.ensure_tables_presences(cursor)
        try:
            yield cursor
            conn.commit()
        finally:
            conn.close()

    # --- --- Databases --- ---
    # --- --- Exports --- ---
    def sql_export(self):
        """
        Export a maximum of data in the sql database.
        """
        self._sql_export_main()
        self._sql_export_metadata()
        self._sql_export_keywords()
        self._sql_export_distances()
        self._sql_export_time_stamps()

    def _sql_export_main(self):
        command = [
            f"INSERT OR REPLACE INTO {self.main_table_name}",
            "(",
            "VALUES (" + ", ".join(["?"] * len(self.default_header)) + ")",
        ]
        format_list = []
        self_dict = self.to_dict()
        for cat_name in self.default_header:
            command[1] += self.sql_compatible_header_keyword(cat_name) + ", "

            if str(self_dict[cat_name]).lower() not in ("", "none", "undefined", "n/a", "?"):
                value = self_dict[cat_name]
            else:
                value = None

            format_list.append(value)

        command[1] = command[1].removesuffix(", ") + ")"

        true_command = " ".join(command) + ";"

        with self.write_in_database() as cursor:
            cursor.execute(true_command, format_list)

    def _sql_export_metadata(self):
        if not self.metadata:
            return None

        format_list = []
        command = [
            f"INSERT OR REPLACE INTO {self.metadata_table_name}(url, key, value)",
            "VALUES",
        ]
        for key, value in self.metadata.items():
            command.append("(?, ?, ?),")
            format_list.extend([self.url, key, value])

        return self._sql_finalise_export(command, format_list)

    def _sql_export_keywords(self):
        # Is there anything to do ?
        if not self.keywords:
            return None

        # Prepare command
        command = [
            f"INSERT OR REPLACE INTO {self.keywords_table_name}(url, keyword, occurrence)",
            "VALUES",
        ]
        format_list = []

        # Fill command / format_list
        for keyword, occurrences in self.keywords.items():
            if occurrences == -1:
                # Do not flood database with useless values
                continue

            command.append("(?, ?, ?),")
            format_list.extend([self.url, keyword, occurrences])

        return self._sql_finalise_export(command, format_list)

    def _sql_export_distances(self):
        # Is there anything to do ?
        if not self.distances:
            return None

        # Prepare sql command
        command = [
            f"INSERT OR REPLACE INTO {self.distances_table_name}(localisation1, localisation2, distance)",
            "VALUES",
        ]
        format_list = []

        # Fill command / format_list
        for localisation, distance in self.distances.items():
            if distance == -1:
                # Do not flood database with useless values
                continue

            loc1, loc2 = self.sort_localisations(
                self.localisation, localisation
            )
            format_list.extend([loc1, loc2, distance])
            command.append("(?, ?, ?),")

        return self._sql_finalise_export(command, format_list)

    def _sql_export_time_stamps(self):
        if not self._time_stamps:
            return None

        format_list = []
        command = [
            f"INSERT OR REPLACE INTO {self.time_stamps_table_name}(url, keyword, time_stamp)",
            "VALUES",
        ]
        for key, value in self.time_stamps.items():
            command.append(f"(?, ?, ?),")
            format_list.extend([self.url, key, time.strftime("%Y-%m-%d %H:%M:%S", value)])

        return self._sql_finalise_export(command, format_list)

    def _sql_finalise_export(self, command: list[str], format_list: list[AnyType]) -> None:
        command[-1] = command[-1].removesuffix(",") + ";"

        if not format_list:
            # Nothing to do
            return

        true_command = "\n".join(command)

        with self.write_in_database() as cursor:
            cursor.execute(true_command, format_list)

    # --- --- Exports --- ---
    # --- --- --- --- Sqlite --- --- ---

    @staticmethod
    def get_unique_file_name(file_path, ext):
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
    # test = ScrapperObjectCore("Test1'", 'Paris"', "https://google.com", "CDD", "Biology", fake='True', second="3")
    # test.keywords["Alpha'"] = 34
    # test.keywords['Beta"'] = 35
    # test.distances['Alpha"'] = 34.345
    # test.distances["Beta'"] = 35.250
    # test.time_stamps['Alpha"'] = time.localtime()
    # test.time_stamps["Beta'"] = time.localtime()
    # print(test.sql_export())
    pass
