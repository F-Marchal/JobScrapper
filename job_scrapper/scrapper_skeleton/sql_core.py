import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Sequence

# pylint: disable=E0611
from mypy.types_utils import AnyType

from .object_core import ScrapperObjectCore


class ScrapperSQLightCore(ScrapperObjectCore):
    """
    Specialisation of ScrapperObjectCore that allows
    SQL exports and add the creation of an SQL database
    """
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
                "last_sighting"
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

        with self.write_in_database() as cursor:
            cursor.execute(true_command, format_list)

    # --- --- Exports --- ---
    @classmethod
    def list_to_sql(cls, jobs: Sequence["ScrapperSQLightCore"]):
        """
        Export a list of job inside the sql database.
        :param list ["ScrapperObjectCore"] jobs: A list of ScrapperObjectCore
        :return:
        """
        cls.logger.debug("Exporting %s jobs to sql database", len(jobs))
        for job_obj in jobs:
            job_obj.sql_export()

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
