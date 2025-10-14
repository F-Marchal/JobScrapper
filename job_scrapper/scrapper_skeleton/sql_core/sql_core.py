import logging
import os
import datetime
from sqlalchemy import create_engine

from .sql_tables import BaseTableForJobScrapper, Jobs, Metadata, TimeStamps, Distances
from sqlalchemy.orm import sessionmaker
import sqlite3
import time
from contextlib import contextmanager
from typing import Sequence, Union, Generator, Any
import re
# pylint: disable=E0611
from sqlalchemy.orm import Session, Query


import unicodedata
from ..object_core import ScrapperObjectCore

from .sql_tables import BaseTableForJobScrapper, Jobs, Metadata, TimeStamps, Distances, Keywords
from sqlalchemy.orm import sessionmaker
class ScrapperSQLightCore(ScrapperObjectCore):
    """
    Specialisation of ScrapperObjectCore that allows
    SQL exports and add the creation of an SQL database
    """

    _database_file_name: str = "JobsDatabase"
    _tables: dict[str, BaseTableForJobScrapper] = {
        Jobs.__tablename__: Jobs,
        Metadata.__tablename__: Metadata,
        TimeStamps.__tablename__: TimeStamps,
        Distances.__tablename__: Distances,
        Keywords.__tablename__: Keywords,
    }
    first_sighting_time_stamp_name = "First sighting"

    @classmethod
    def get_known_databases(cls) ->  dict[str, dict[str, Any]]:
        return BaseTableForJobScrapper.get_known_databases()

    @classmethod
    def get_tables(cls):
        return cls._tables.copy()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get older first sighting date
        fstsn = self.first_sighting_time_stamp_name
        with self.get_maindb_session() as session:
            result = (
                session.query(TimeStamps.time_stamp)
                .filter(
                    TimeStamps.url == self.url,
                    TimeStamps.label == fstsn
                )
                .all()
            )

        if result:
            first_sighting = result[-1][0].timetuple()

        else:
            # If this is the first time we see this offer,
            # then first_sighting_time_stamp_name = self.init_time_stamp_name
            first_sighting = self.retrieve_time_stamps(self.init_time_stamp_name)

        self.add_time_stamps(fstsn, first_sighting)


    @classmethod
    @contextmanager
    def get_maindb_session(cls, workdir: str | None = None):
        path = cls.get_maindb_path(workdir)
        with Jobs.get_session(database_path=path, logger=cls.logger) as session:
            yield session

    @classmethod
    @contextmanager
    def get_archive_session(cls, workdir: str | None = None):
        path = cls.get_archive_path(workdir)
        with Jobs.get_session(database_path=path, logger=cls.logger) as session:
            yield session

    available_databases = {
        "maindb": get_maindb_session,
        "archive": get_archive_session
    }

    #  --- --- --- --- Sqlite --- --- --- ----
    # --- --- Names and paths --- ---
    @classmethod
    def get_maindb_path(cls, workdir: str | None = None, ext: str = ".db"):
        """
        :param str workdir: a path to a directory
        :param str ext: Database file extension
        :return str: A path that lead to a database file.
        """
        if not workdir:
            workdir = cls.get_workdir()

        file_path = os.path.abspath(
            os.path.join(workdir, cls._database_file_name)
        )

        if file_path[-len(ext):] != ext:
            file_path += ext

        return file_path


    @classmethod
    def get_archive_path(cls, workdir: str | None = None):
        """
        :param str workdir: a path to a directory
        :return str: A path that lead to a database file.
        """
        return cls.get_maindb_path(workdir, ext=".archive.db")

    # --- --- Names and paths --- ---
    # --- --- Exports --- ---
    def sql_export(self, session: Session):
        """
        Export a maximum all field inside the selected database.
        Use self.get_[database]_session to obtain a session
        """
        self.logger.debug(f"Exporting '%s' using '%s'", self, session)

        self._sql_export_main(session)
        self._sql_export_metadata(session)
        self._sql_export_keywords(session)
        self._sql_export_time_stamps(session)
        self._sql_export_distances(session)

        self.logger.debug(f"'%s' exported using '%s'", self, session)

    def _sql_export_main(self, session: Session) -> None:
        job_obj = Jobs(
            url = self.url,
            title = self.title,
            localisation = self.localisation,
            contract = self.contract_type,
            field = self.field,
            origin = self.get_class_name()
        )
        session.add(job_obj)

    def _sql_export_metadata(self, session: Session) -> None:
        for key, value in self.metadata.items():
            metadat_obj = Metadata(
                url=self.url,
                key=key,
                value=value
            )
            session.add(metadat_obj)

    def _sql_export_keywords(self, session: Session) -> None:
        for keyword, occurrence in self.keywords.items():
            key_obj = Keywords(
                url=self.url,
                keyword=keyword,
                occurrence=occurrence if occurrence != -1 else None
            )
            session.add(key_obj)

    def _sql_export_time_stamps(self, session: Session) -> None :
        for label, t_struct in self.time_stamps.items():
            time_obj = TimeStamps(
                url=self.url,
                label=label,
                time_stamp=datetime.datetime(
                    t_struct.tm_year, t_struct.tm_mon, t_struct.tm_mday,
                    t_struct.tm_hour, t_struct.tm_min, t_struct.tm_sec
                ),
            )
            session.add(time_obj)

    def _sql_export_distances(self, session: Session):
        for reference_localisation, distance in self.distances.items():
            dist_obj = Distances(
                job_localisation=self.localisation,
                reference_localisation=reference_localisation,
                distance=distance if distance != -1 else None,
            )
            session.add(dist_obj)


    @classmethod
    def _sql_batch_export(cls, session: Session, *jobs: 'ScrapperSQLightCore'):
        for job in jobs:
            job.sql_export(session)

    @classmethod
    def sql_batch_export(cls, *jobs: 'ScrapperSQLightCore', database_name: str | None = None, workdir: None | str = None):
        if database_name is None:
            database_session_command = cls.get_maindb_session

        elif database_name in cls.available_databases:
            database_session_command = cls.available_databases[database_name]

        else:
            raise Keywords(f"<database_name> should be in `None` or in {cls.available_databases.keys()}."
                           f" Got '{database_name}'")

        with database_session_command(workdir=workdir) as session:
            cls.logger.debug("Exporting %s job offers...", len(jobs))
            cls._sql_batch_export(session, *jobs)
            cls.logger.debug("%s job offer exported !", len(jobs))

    # --- --- Exports --- ---
    # --- --- Imports --- ---
    @classmethod
    def sql_import_jobs(cls, session: Session, request: Query | None = None) -> 'list[ScrapperSQLightCore]':
        if not request:
            request = Jobs.get_all(session)
        loaded_jobs = []

        for job_entry in request.all():
            new_jobs = cls(
                contract_type=job_entry.contract,
                field = job_entry.field,
                localisation = job_entry.localisation,
                title = job_entry.title,
                url = job_entry.url,
            )

            for time_stamp_entry in TimeStamps.get_associated_time_stamps(session, new_jobs.url):
                new_jobs.add_time_stamps(time_stamp_entry.label, time_stamp_entry.time_stamp.timetuple())

            for keywords_entry in Keywords.get_associated_keywords(session, new_jobs.url):
                occurrence = keywords_entry.occurrence
                if occurrence is None:
                    occurrence = -1

                new_jobs.add_keyword_count(keywords_entry.keyword, occurrence)

            for distances_entry in Distances.get_associated_distances(session, new_jobs.localisation):
                distance = distances_entry.distance
                if distance is None:
                    distance = -1

                new_jobs.add_distance_to(distances_entry.reference_localisation, distance)

            for metadata_entry in Metadata.get_associated_metadata(session, new_jobs.url):
                new_jobs.add_metadata(metadata_entry.key, metadata_entry.value)

            loaded_jobs.append(new_jobs)
        return loaded_jobs



    # --- --- Imports --- ---
    # --- --- Utils --- ---

    # --- --- Utils --- ---

    '''    # --- --- Names and paths --- ---
    # --- --- Exports --- ---
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
        return cls.get_sql_table_column_name(cls._main_table_name)

    @classmethod
    def get_sql_column_metadata_table(cls):
        """Returns columns names attached to metadata table"""
        return cls.get_sql_table_column_name(cls._metadata_table_name)

    @classmethod
    def get_sql_column_distances_table(cls):
        """Returns columns names attached to distances table"""
        return cls.get_sql_table_column_name(cls._distances_table_name)

    @classmethod
    def get_sql_column_time_stamps_table(cls):
        """Returns columns names attached to time stamps table"""
        return cls.get_sql_table_column_name(cls._time_stamps_table_name)

    @classmethod
    def get_sql_column_keywords_table(cls):
        """Returns columns names attached to keywords table"""
        return cls.get_sql_table_column_name(cls._keywords_table_name)

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
        return cls.get_sql_column_content(cls._distances_table_name, "reference_localisation", distinct=True)

    @classmethod
    def get_sql_keywords(cls):
        return cls.get_sql_column_content(cls._keywords_table_name, "keyword", distinct=True)

    @classmethod
    def get_sql_timestamps(cls):
        return cls.get_sql_column_content(cls._time_stamps_table_name, "time_stamp", distinct=True)

    @classmethod
    def get_sql_metadata(cls):
        return cls.get_sql_column_content(cls._metadata_table_name, "key", distinct=True)

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
'''