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
    def sql_describe_table(
        cls, table: str
    ) -> list[tuple[Union[str, int, None], ...]]:
        command = f"PRAGMA table_info('{table}');"
        return cls.sql_run(command)

    @classmethod
    def sql_table_column_name(cls, table: str) -> list[str]:
        return [str(tup[1]) for tup in cls.sql_describe_table(table) if tup]

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
    def parse_sql_generate_command_from_list(cls, table: str, column: str, *items: str, no_condition_allowed: bool = True,):
        legal_names = cls.sql_column_content(table, column, distinct=True)
        pattern = re.compile("|".join(legal_names))
        cls.logger.debug("Parsing : %s", items)

        result = []
        for strings in items:
            pattern_found = re.search(pattern, strings)
            if not pattern_found:
                cls.logger.warning(f"Ignoring unknown {table}.{column}'s value: '%s'\n"
                                   f"Valid values are %s", strings, legal_names)
                continue

            pos1, pos2 = pattern_found.span()


            reference = strings[pos1:pos2]
            if pos1 != 1:
                sql_condition = "OR"

            else:
                if strings[0].upper() in ("&", "A"):
                    sql_condition = "AND"

                elif strings[0].upper() in ("|", "O"):
                    sql_condition = "OR"

                elif strings[0].upper() in ("^", "X"):
                    sql_condition = "XOR"

                else:
                    cls.logger.warning("Unknown condition replaced by OR : '%s'."
                                    "Please ues '&', 'A' (AND), '|', 'O' (OR), '^', 'X' (WOR) ",  strings[0])
                    sql_condition = "OR"

            condition = strings[pos2:]


            if condition and no_condition_allowed:
                cls.logger.warning(f"%s.%s does not support condition. Ignoring condition : %s", table, column, strings)
                result.append((reference, None, None, None))
                continue
            if not condition:
                result.append((reference, None, None, None))
                continue


            if condition[0] == "!":
                operator = "<>"
            elif condition[0] in (">", "<", "="):
                operator = condition[0]
            else:
                cls.logger.warning("Ignoring condition ('%s') : "
                                   "Unknown operator ('%s'). (Use '<', '>', '=', '!')", strings, condition[0])
                continue


            if len(condition) == 1:
                cls.logger.warning("Ignoring condition ('%s') : Missing value after '%s'", strings, operator)
                continue


            try:
                value = float(condition[1:])
            except ValueError as error:
                cls.logger.warning("Can not parse '%s' : %s", condition[1:], error)
                continue


            result.append((reference, operator, value, sql_condition))

        return result

    @dataclass
    class SQLCommandFormater:
        select_command: list[str] = field(default_factory=list)
        join_command: list[str] = field(default_factory=list)
        where_command: list[str] = field(default_factory=list)
        having_command: list[str] = field(default_factory=list)
        group_by_command:  list[str] = field(default_factory=list)

        select_command_conclusion: list[str] = field(default_factory=list)
        join_command_conclusion: list[str] = field(default_factory=list)
        having_command_conclusion: list[str] = field(default_factory=list)

        select_arguments: list[str | int | None] = field(default_factory=list)
        join_arguments: list[str | int | None] = field(default_factory=list)
        where_arguments: list[str | int | None] = field(default_factory=list)
        having_arguments: list[str | int | None] = field(default_factory=list)

        @staticmethod
        def _construct(
                command,
                end_command,
                start_keyword="",
                end_keyword="",
                start_join=",\n\t",
                end_join=" "
        ) -> str:
            return (f"{start_keyword}"
                    f"{start_join.join(command)}"
                    f"\n{end_keyword}"
                    f"{end_join.join(end_command)}\n")


        def _construct_select(self, command: str, command_arg: list, select=True, from_=True):
            command += self._construct(
                self.select_command,
                self.select_command_conclusion,
                start_keyword= "SELECT\n\t" if select else "",
                end_keyword="FROM\n\t" if from_ and self.select_command_conclusion else "",
            )
            command_arg.extend(self.select_arguments)
            return command

        def _construct_join(self, command: str, command_arg: list):
            command += self._construct(
                self.join_command,
                self.join_command_conclusion,
                start_keyword= "",
                end_keyword="",
                start_join="\n\t",
                end_join="",
            )
            command_arg.extend(self.join_arguments)
            return command

        def _construct_where(self, command: str, command_arg: list, where=True):
            command += self._construct(
                self.join_command,
                self.join_command_conclusion,
                start_keyword="WHERE\n\t" if where else "",
                end_keyword="",
                start_join="",
                end_join="",
            )
            command_arg.extend(self.join_arguments)
            return command

        def _construct_having(self, command: str, command_arg: list, having=True):
            command +=  self._construct(
                self.having_command,
                self.having_command_conclusion,
                start_keyword= "HAVING\n\t" if having else "",
                end_keyword="",
                start_join = "\n\t",
            )
            command_arg.extend(self.having_arguments)
            return command

        def construct(self, select=True, from_=True, where=True, having=True,):
            command = ""
            command_arg = []

            # Select
            command = self._construct_select(
                command,
                command_arg,
                select,
                from_
            )

            if self.join_command:
                # Join
                command = self._construct_join(
                    command,
                    command_arg,
                )

            if self.where_command:
                command = self._construct_where(
                    command,
                    command_arg,
                    where
                )

            # Group by is mandatory for Having close
            if not self.group_by_command:
                return command, command_arg


            command += "GROUP BY " + ",\n\t".join(self.group_by_command) + "\n"

            if self.having_command:
                command = self._construct_having(
                    command,
                    command_arg,
                    having
                )

            return command, command_arg

    @staticmethod
    def _format_sql(command: str, args: list | tuple) -> str:
        result = command
        for val in args:
            if isinstance(val, str):
                val_str = "'" + val.replace("'", "''") + "'"  # échappe les quotes SQL
            elif val is None:
                val_str = "NULL"
            else:
                val_str = str(val)
            result = result.replace("?", val_str, 1)
        return result

    @classmethod
    def _sql_generate_command_from_list(
            cls,
            conditions: list[str],
            scf: 'SQLCommandFormater',
            main_table: str,
            main_join_on: str,
            second_table: str,
            second_join_on: str,
            column_to_check :str,
            column_to_keep: str,
            relax: bool = False,
            suffix: str = "_col",
            first_operator_exist: bool = False,
            having_condition: str = "",
            no_condition_allowed: bool = False,
    ):
        result = cls.parse_sql_generate_command_from_list(second_table, column_to_check, *conditions, no_condition_allowed=no_condition_allowed)
        opened_parenthesis = False
        # Select
        renaming = f"MAX(CASE WHEN {second_table}.{column_to_check} = ? THEN {second_table}.{column_to_keep} END) AS"

        for (reference, operator, value, sql_condition) in result:
            # Select
            reference_column_name = cls.sql_compatible_header_keyword(f"{reference}{suffix}")
            scf.select_command.append(f'{renaming} {reference_column_name}')

            # Join
            scf.join_arguments.append(reference)
            scf.select_arguments.append(reference)

            if not operator:
                continue

            # Having
            if not first_operator_exist:
                sql_condition = ""
                first_operator_exist = True

            if not opened_parenthesis:
                if having_condition:
                    scf.having_command.append(having_condition)
                scf.having_command.append("(")
                opened_parenthesis = True

            if relax:
                having_command = f"{sql_condition} ({reference_column_name} {operator} ? OR {reference_column_name} IS NULL)"
            else:
                having_command = f"{sql_condition} {reference_column_name} {operator} ?"

            scf.having_command.append(having_command)
            scf.having_arguments.append(value)

        if opened_parenthesis:
            scf.having_command.append(")")


        scf.join_command.extend([
            f"LEFT JOIN {second_table}",
            f"ON {main_table}.{main_join_on} = {second_table}.{second_join_on}",
            f"AND {second_table}.{column_to_check} IN ({', '.join(['?'] * len(result))})"
        ])

        return first_operator_exist


    @classmethod
    def _sql_generate_command_select(
            cls,
            columns: list[str],
            scf: 'SQLCommandFormater',
    ):
        valid_column_name = set(cls.sql_table_column_name(cls.main_table_name))
        if len(columns) != len(set(columns)):
            raise IndexError(f"<columns> isn't allowed to contain any duplicates. {columns}")

        for column_name in columns:
            if column_name not in valid_column_name:
                cls.logger.warning(
                    f"Invalid column name for %s. Column ignored : %s."
                    f"\nValid names are %s", cls.main_table_name, column_name, valid_column_name
                )
                columns.remove(column_name)
                continue

            scf.select_command.append(f"{cls.main_table_name}.{column_name}")

    @classmethod
    def sql_generate_command(
            cls,
            columns: list[str] = None,
            columns_filters: list[str] = None,
            distances_from: list[str]=None,
            keywords: list[str]=None,
            metadata: list[str] = None,
            distance_relax: bool=False,
            keyword_relax: bool=False,
            metadata_relax: bool = False,
    ):

        #
        if not columns:
            columns = [cls.sql_compatible_header_keyword(item).lower() for item in cls.default_header]

        command_formater = cls.SQLCommandFormater()
        cls._sql_generate_command_select(columns, command_formater)

        command_formater.select_command_conclusion.append(f"{cls.main_table_name}")
        command_formater.group_by_command.append(f"{cls.main_table_name}.url")

        having_condition = ""

        if keywords:
            cls._sql_generate_command_from_list(
                keywords,
                command_formater,
                main_table=cls.main_table_name,
                main_join_on="url",
                second_table=cls.keywords_table_name,
                second_join_on="url",
                column_to_check="keyword",
                column_to_keep="occurrence",
                relax=keyword_relax,
                suffix="_occurence",
                having_condition=having_condition
            )
            having_condition = "AND"


        if distances_from:
            cls._sql_generate_command_from_list(
                distances_from,
                command_formater,
                main_table=cls.main_table_name,
                main_join_on="localisation",
                second_table=cls.distances_table_name,
                second_join_on="job_localisation",
                column_to_check="reference_localisation",
                column_to_keep="distance",
                relax=distance_relax,
                suffix="_km",
                having_condition=having_condition
            )
            having_condition = "AND"

        if metadata:
            cls._sql_generate_command_from_list(
                metadata,
                command_formater,
                main_table=cls.main_table_name,
                main_join_on="url",
                second_table=cls.metadata_table_name,
                second_join_on="url",
                column_to_check="key",
                column_to_keep="value",
                relax=keyword_relax,
                suffix="_metadata",
                having_condition=having_condition,
                no_condition_allowed=True,
            )
            having_condition = "AND"



        # Conclude


        command, args = command_formater.construct()
        print(len(cls.sql_run(command, *args)))

    @classmethod
    def sql_run_display_command(cls, command: str, *args, sep="\t"):
        results = cls.sql_run_with_header(command, *args)

        print("#Command :")
        print(cls._format_sql(command, args))
        print()
        print("#Results :")
        print(len(results) -1, "jobs")
        print()
        print("#" + sep.join([header[0] for header in results[0]]))
        for job in results[1:]:
            print(sep.join([str(item) for item in job]))


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
