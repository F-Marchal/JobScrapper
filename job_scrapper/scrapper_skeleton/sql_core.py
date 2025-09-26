import logging
import os
import pathlib
import sqlite3
import time
from contextlib import contextmanager
from typing import Sequence, Union
import re
# pylint: disable=E0611
from mypy.types_utils import AnyType

from .object_core import ScrapperObjectCore
from dataclasses import dataclass, field

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

    # TODO: Utiliser dans creation / export ?
    _tables = {
        main_table_name: [],
        metadata_table_name: [],
        keywords_table_name: [],
        distances_table_name: [],
        time_stamps_table_name: [],
    }

    _sql_command_folder = (
        pathlib.Path(__file__).parent.resolve().joinpath("sql")
    )

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
        if keyword[0] == '#':
            keyword = keyword[1:]
        return re.sub(r'[^0-9a-zA-Z_]', '_', keyword.strip()).replace("__", "_")

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
        print(database_command)
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
            + "reference_localisation TEXT NOT NULL,"
            + "job_localisation TEXT NOT NULL,"
            + "distance REAL NOT NULL,"
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
            "url TEXT KEY,",
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
            if occurrences == -1 or occurrences == 0:
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
            f"INSERT OR REPLACE INTO {self.distances_table_name}(reference_localisation, job_localisation, distance)",
            "VALUES",
        ]
        format_list = []

        # Fill command / format_list
        for localisation, distance in self.distances.items():
            if distance == -1:
                # Do not flood database with useless values
                continue

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
        Export a list of job inside the sql database.
        :param list ["ScrapperObjectCore"] jobs: A list of ScrapperObjectCore
        :return:
        """
        cls.logger.debug("Exporting %s jobs to sql database", len(jobs))
        for job_obj in jobs:
            job_obj.sql_export()

    # --- --- Exports --- ---
    # --- --- Requests --- ---
    @classmethod
    def sql_run(cls, command, *args) -> list[tuple[Union[str, int, None], ...]]:
        cls.logger.debug("Running : %s", command)
        with cls.write_in_database() as cursor:
            cursor.execute(command, args)
            return cursor.fetchall()

    @classmethod
    def sql_run_file(cls, name: str) -> list[tuple[Union[str, int, None], ...]]:
        cls.logger.debug("Opening as SQL command : %s", name)
        sql_file = cls._sql_command_folder.joinpath(name)
        with open(sql_file, "r", encoding="utf-8") as f:
            command = f.read()

        return cls.sql_run(command)

    @classmethod
    def sql_table_names(cls) -> list[str]:
        command = """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name;
        """
        return [str(tup[0]) for tup in cls.sql_run(command)]

    @classmethod
    def sql_table_details(
        cls, table: str
    ) -> list[tuple[Union[str, int, None], ...]]:
        command = f"PRAGMA table_info('{table}');"
        return cls.sql_run(command)

    @classmethod
    def sql_table_column_name(cls, table: str) -> list[str]:
        return [str(tup[1]) for tup in cls.sql_table_details(table) if tup]

    @classmethod
    def sql_column_content(
        cls, table: str, column: str, distinct: bool = False
    ) -> list[str | None | int]:
        distinct_kw = "DISTINCT" if distinct else ""
        command = f"SELECT {distinct_kw} {table}.{column} from {table};"
        return [tup[0] for tup in cls.sql_run(command)]


    @classmethod
    def get_sql_reference_places(cls):
        return cls.sql_column_content("Distances", "reference_localisation", distinct=True)


    @classmethod
    def parse_distances(cls, *distances: str):
        reference_localisations = cls.get_sql_reference_places()
        pattern = re.compile("|".join(reference_localisations))
        cls.logger.debug("Parsing distances : %s", distances)

        result = []
        for strings in distances:
            pattern_found = re.findall(pattern, strings)
            if not pattern_found:
                logging.warning("Ignoring unknown localisation : '%s'", strings)
                continue

            reference = pattern_found[0]
            condition = strings[len(reference):]

            if not condition:
                result.append((reference, None, None))
                continue


            if condition[0] in (">", "<"):
                operator = condition[0]
            else:
                cls.logger.warning("Ignoring localisation ('%s') : "
                                   "Unknown operator ('%s'). (Use '<', '>')", strings, condition[0])
                continue


            if len(condition) == 1:
                cls.logger.warning("Ignoring localisation ('%s') : Missing value after '%s'", strings, operator)
                continue


            try:
                value = float(condition[1:])
            except ValueError as error:
                cls.logger.warning("Can not parse '%s' : %s", condition[1:], error)
                continue

            result.append((reference, operator, value))

        return result

    @dataclass
    class SQLCommandFormater:
        select_command: list[str] = field(default_factory=list)
        join_command: list[str] = field(default_factory=list)
        having_command: list[str] = field(default_factory=list)
        select_arguments: list[str] = field(default_factory=list)
        join_arguments: list[str] = field(default_factory=list)
        having_arguments: list[str] = field(default_factory=list)

        def construct(self):
            print(""
            + "\n\t".join(self.select_command)
            + "\n\t".join(self.join_command)
            + "\n\t".join(self.having_command)
            )

    @classmethod
    def _sql_main_generate_distance_command(
            cls,
            distances_from: list[str],
            scf: 'SQLCommandFormater'
    ):
        result = cls.parse_distances(*distances_from)
        tab = cls.distances_table_name
        # Select
        renaming = f"MAX(CASE WHEN {tab}.reference_localisation = ? THEN {tab}.distance END) AS ?"

        for (reference, operator, value) in result:
            # Select
            reference_column_name = cls.sql_compatible_header_keyword(f"{reference}_km")
            scf.select_command.append(renaming)
            scf.select_arguments.append(reference)

            # Join
            scf.join_arguments.append(reference)

            if operator:
                # Having
                scf.having_command.append(f"{reference_column_name} {operator} ?")
                scf.having_arguments.append(value)


        scf.join_command.extend([
            "LEFT JOIN Distances",
            f"\tON Jobs.localisation = {tab}.job_localisation",
            f"\tAND Distances.reference_localisation IN ({', '.join(['?'] * len(result))})"
        ])

    # TODO Dict tab format

    @classmethod
    def sql_main(cls, distances_from: list[str]):
        import pprint
        command_formater = cls.SQLCommandFormater()
        command_formater.select_command.append(f"Select {cls.main_table_name}.*")
        cls._sql_main_generate_distance_command(distances_from, command_formater)
        command_formater.construct()

        # Conclude
        command_formater.select_command.append(f"FROM {cls.main_table_name}")


    """
        @classmethod
        def sql_main_generate_distance_command(cls, distances_from: list[str]):
            result = cls.parse_distances(*distances_from)
    
            # Select
            renaming = "MAX(CASE WHEN Distances.reference_localisation = ? THEN Distances.distance END) AS {}"
            reference_translation = {}
            select_arguments = []
            select_command = []
    
            # Join
            join_arguments = []
    
            # Having
            having_command = []
            having_arguments = []
    
    
            for (reference, operator, value) in result:
                # Select
                reference_column_name = cls.sql_compatible_header_keyword(f"{reference}_km")
                reference_translation[reference] = reference_column_name
                select_command.append(renaming.format(reference_column_name))
                select_arguments.append(reference)
    
                # Join
                join_arguments.append(reference)
    
                if operator:
                    # Having
                    having_command.append(f"{reference_column_name} {operator} ?")
                    having_arguments.append(value)
    
    
            join_string_command = (
                "LEFT JOIN Distances\n"
                "ON Jobs.localisation = Distances.job_localisation\n"
                f"AND Distances.reference_localisation IN ({', '.join(['?'] * len(join_arguments))})\n"
            )
    
            return {
                "select": (",\n\t".join(select_command), select_arguments),
                "join": (join_string_command, join_arguments),
                "having": (" AND\n\t".join(having_command), having_arguments)
            }
    
    
        @classmethod
        def sql_main(cls, distances_from: list[str]):
            distance_command_parts = cls.sql_main_generate_distance_command(distances_from)
    
            comm = "SELECT Jobs.*, " + \
                distance_command_parts["select"][0] + \
                " FROM Jobs " + \
                distance_command_parts["join"][0] + \
                "GROUP BY Jobs.url HAVING " + \
                distance_command_parts["having"][0] + \
                ";"
    
            print(comm)
    
            print(cls.sql_run(comm, *[*distance_command_parts["select"][1], *distance_command_parts["join"][1], *distance_command_parts["having"][1]]))
    """

    # --- --- Requests --- ---
    # --- --- --- --- Sqlite --- --- ---

# TODO Dict tab format
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
