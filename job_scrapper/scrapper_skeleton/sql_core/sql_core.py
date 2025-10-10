import os

import sqlite3
import time
from contextlib import contextmanager
from typing import Sequence, Union
import re
# pylint: disable=E0611
from mypy.types_utils import AnyType

import unicodedata
from ..object_core import ScrapperObjectCore

class ScrapperSQLightCore(ScrapperObjectCore):
    """
    Specialisation of ScrapperObjectCore that allows
    SQL exports and add the creation of an SQL database
    """

    database_file_name = "AllJobs"

    main_table_name = "Jobs"
    metadata_table_name = "Metadata"
    keywords_table_name = "KeywordsCount"
    distances_table_name = "Distances"
    time_stamps_table_name = "TimeStamps"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # first_sighting
        with self.write_in_database() as cursor:
            cursor.execute(
                """
                select time_stamp from TimeStamps where TimeStamps.url=? and TimeStamps.keyword="first_sighting";
                """,
                [self.url],
            )
            result = cursor.fetchall()

        if result:
            try:
                self._time_stamps["first_sighting"] = time.strptime(
                    result[-1][0], "%Y-%m-%d %H:%M:%S"
                )
            except ValueError as ve:
                self.logger.error(
                    "Error during loading of the 'first_sighting' time_stamp of '%s' : \n %s",
                    self.url,
                    ve,
                )
        else:
            self._time_stamps["first_sighting"] = self._time_stamps[
                self.init_time_stamp_name
            ]

    #  --- --- --- --- Sqlite --- --- --- ----
    # --- --- Names and paths --- ---

    @classmethod
    def get_database_path(cls, workdir: str | None = None):
        """
        :param str workdir: a path to a directory
        :return str: A path that lead to a database file.
        """
        if not workdir:
            workdir = cls.get_workdir()

        return os.path.abspath(
            os.path.join(workdir, cls.database_file_name + ".db")
        )

    @classmethod
    def sql_header_compatible_string(cls, name: str):
        """
        Transform a string to ensure that a keyword can be used as
        header inside a sql_core table.
        :param str name: the string you want to use.
        :return str: a string that can be used as a sql_core table header
        """
        name = unicodedata.normalize('NFD', name)
        name = name.encode('ascii', 'ignore').decode('utf-8')

        if name[0] == '#':
            name = name[1:]

        name = re.sub(r'[^0-9a-zA-Z_]', '_', name.strip())
        name = re.sub(r'_+', '_', name)
        name = name.strip("_")

        if not name:
            return "Unable_to_use_as_header"

        return name

    # --- --- Names and paths --- ---
    # --- --- Databases --- ---
    @classmethod
    def _create_main_sql_table_command(cls) -> str:
        database_definition = [
            f"CREATE TABLE IF NOT EXISTS  {cls.main_table_name} (",
        ]
        for column_name, column_type in cls.default_header.items():
            column_name = cls.sql_header_compatible_string(column_name)
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
            "url TEXT,",
            "keyword TEXT NOT NULL,",
            "occurrence INT,",
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
            + "reference_localisation TEXT NOT NULL,"
            + "job_localisation TEXT NOT NULL,"
            + "distance REAL,"
            + "PRIMARY KEY(reference_localisation, job_localisation)"
            ");"
        )

    @classmethod
    def _create_time_stamps_sql_table_command(cls):
        """
        :return str: The command that allow the creation of the time stamps table.
        """
        command = [
            f"CREATE TABLE IF NOT EXISTS {cls.time_stamps_table_name} (",
            "url TEXT,",
            "keyword TEXT NOT NULL,",
            "time_stamp DATE NOT NULL,",
            "PRIMARY KEY(url, keyword),"
            f"FOREIGN KEY (url) REFERENCES {cls.main_table_name}(url)",
            ");",
        ]
        return "\n".join(command)

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
        Export a maximum of data in the sql_core database.
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
            command[1] += self.sql_header_compatible_string(cat_name) + ", "

            if str(self_dict[cat_name]).lower() not in (
                "",
                "none",
                "undefined",
                "n/a",
                "?",
            ):
                value = self_dict[cat_name]
            else:
                value = None

            format_list.append(value)

        command[1] = command[1].removesuffix(", ") + ")"

        true_command = " ".join(command) + ";"

        self.sql_run(true_command, *format_list)

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
                occurrences = None

            command.append("(?, ?, ?),")
            format_list.extend([self.url, keyword, occurrences])

        return self._sql_finalise_export(command, format_list)

    def _sql_export_distances(self):
        # Is there anything to do ?
        if not self.distances:
            return None

        # Prepare sql_core command
        command = [
            f"INSERT OR REPLACE INTO {self.distances_table_name}(reference_localisation, job_localisation, distance)",
            "VALUES",
        ]
        format_list = []

        # Fill command / format_list
        for localisation, distance in self.distances.items():
            if distance == -1:
                distance = None

            format_list.extend([localisation, self.localisation, distance])
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
            command.append("(?, ?, ?),")
            format_list.extend(
                [self.url, key, time.strftime("%Y-%m-%d %H:%M:%S", value)]
            )

        return self._sql_finalise_export(command, format_list)

    def _sql_finalise_export(
        self, command: list[str], format_list: list[AnyType]
    ) -> None:
        command[-1] = command[-1].removesuffix(",") + ";"

        if not format_list:
            # Nothing to do
            return

        true_command = "\n".join(command)

        self.sql_run(true_command, *format_list)

    @classmethod
    def list_to_sql(cls, jobs: Sequence["ScrapperSQLightCore"]):
        """
        Export a list of job inside the sql_core database.
        :param list ["ScrapperObjectCore"] jobs: A list of ScrapperObjectCore
        :return:
        """
        cls.logger.debug("Exporting %s jobs to sql_core database", len(jobs))
        for job_obj in jobs:
            job_obj.sql_export()

    # --- --- Exports --- ---
    # --- --- Requests --- ---
    # --- run ---
    @classmethod
    def sql_run(cls, command, *args) -> list[tuple[Union[str, int, None], ...]]:
        cls.logger.debug("Running : \n%s",  cls._format_sql(command, args))
        with cls.write_in_database() as cursor:
            cursor.execute(command, args)
            return cursor.fetchall()

    @classmethod
    def sql_run_with_header(cls, command, *args) -> list[tuple[Union[str, int, None, bool], ...]]:
        cls.logger.debug("Running : \n%s",  cls._format_sql(command, args))
        with cls.write_in_database() as cursor:
            cursor.execute(command, args)
            return [cursor.description, *cursor.fetchall()]

    @classmethod
    def sql_run_file(cls, sql_file: str) -> list[tuple[Union[str, int, None], ...]]:
        cls.logger.debug("Opening as SQL command : %s", sql_file)
        with open(sql_file, "r", encoding="utf-8") as f:
            command = f.read()

        return cls.sql_run(command)

    # --- run ---
    # --- describe commands ---
    @classmethod
    def get_sql_table_names(cls) -> list[str]:
        command = """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name;
        """
        return [str(tup[0]) for tup in cls.sql_run(command)]

    @classmethod
    def sql_describe_table(
        cls, table: str
    ) -> list[tuple[Union[str, int, None], ...]]:
        command = f"PRAGMA table_info('{table}');"
        return cls.sql_run(command)
    # --- describe commands ---
    # --- columns names ---
    @classmethod
    def get_sql_table_column_name(cls, table: str) -> list[str]:
        """Returns columns names attached to a table"""
        return [str(tup[1]) for tup in cls.sql_describe_table(table) if tup]

    @classmethod
    def get_sql_column_jobs_table(cls):
        """Returns columns names attached to jobs table"""
        return cls.get_sql_table_column_name(cls.main_table_name)

    @classmethod
    def get_sql_column_metadata_table(cls):
        """Returns columns names attached to metadata table"""
        return cls.get_sql_table_column_name(cls.metadata_table_name)

    @classmethod
    def get_sql_column_distances_table(cls):
        """Returns columns names attached to distances table"""
        return cls.get_sql_table_column_name(cls.distances_table_name)

    @classmethod
    def get_sql_column_time_stamps_table(cls):
        """Returns columns names attached to time stamps table"""
        return cls.get_sql_table_column_name(cls.time_stamps_table_name)

    @classmethod
    def get_sql_column_keywords_table(cls):
        """Returns columns names attached to keywords table"""
        return cls.get_sql_table_column_name(cls.keywords_table_name)

    # --- columns names ---
    # --- get commands ---
    @classmethod
    def get_sql_column_content(
        cls, table: str, column: str, distinct: bool = False
    ) -> list[str | None | int]:
        distinct_kw = "DISTINCT" if distinct else ""
        command = f"SELECT {distinct_kw} {table}.{column} from {table};"
        return [tup[0] for tup in cls.sql_run(command)]

    @classmethod
    def get_sql_reference_places(cls):
        return cls.get_sql_column_content(cls.distances_table_name, "reference_localisation", distinct=True)

    @classmethod
    def get_sql_keywords(cls):
        return cls.get_sql_column_content(cls.keywords_table_name, "keyword", distinct=True)

    @classmethod
    def get_sql_timestamps(cls):
        return cls.get_sql_column_content(cls.time_stamps_table_name, "time_stamp", distinct=True)

    @classmethod
    def get_sql_metadata(cls):
        return cls.get_sql_column_content(cls.metadata_table_name, "key", distinct=True)

    # --- get commands ---
    # --- Helpers ---
    @staticmethod
    def _parse_time(date_str: str) -> time.struct_time:
        formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
        i = 0
        result = None
        last_error = None
        while i < len(formats) and result is None:
            try:
                result = time.strptime(date_str, formats[i])
            except ValueError as error:
                i += 1
                last_error = error
                continue

        if result:
            return result
        raise last_error

    @staticmethod
    def _format_sql(command: str, args: list | tuple) -> str:
        result = command

        for val in args:
            if isinstance(val, (str, time.struct_time)):
                val_str = "'" + str(val).replace("'", "''") + "'"  # échappe les quotes SQL
            elif val is None:
                val_str = "NULL"
            else:
                val_str = str(val)
            result = result.replace("?", val_str, 1)

        return result

    # --- Helpers ---
    # --- --- Requests --- ---
    # --- --- --- --- Sqlite --- --- ---

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
