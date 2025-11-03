import os
import datetime
from contextlib import contextmanager
from typing import Any

# pylint: disable=E0611
from sqlalchemy.orm import Session, Query
from sqlalchemy import and_, or_, not_
from sqlalchemy.sql import operators as ope

from job_scrapper.scrapper_skeleton.object_core import ScrapperObjectCore
from sql.tables import BaseTable, Jobs, Metadata, TimeStamps, Distances, Keywords
from sql.tables.request_helpers.job_request import JobRequest

from sql.wrappers.wrapper_comparison import STRING_TO_COMPARISON_WRAPPERS
from sql.wrappers.wrapper_logical import STRING_TO_LOGICAL_WRAPPERS



# TODO: Test that Table.col.name == self.column_name_cleaner(Table.col.name)

class ScrapperSQLightCore(ScrapperObjectCore):
    """
    Specialisation of ScrapperObjectCore that allows
    SQL exports and add the creation of an SQL database
    """

    _database_file_name: str = "JobsDatabase"
    _tables: dict[str, BaseTable] = {
        Jobs.__tablename__: Jobs,
        Metadata.__tablename__: Metadata,
        TimeStamps.__tablename__: TimeStamps,
        Distances.__tablename__: Distances,
        Keywords.__tablename__: Keywords,
    }
    first_sighting_time_stamp_name = "First sighting"

    @classmethod
    def get_job_requester(cls) -> JobRequest:
        return JobRequest(
            suffixes={
                "time_stamp": cls.time_stamp_suffix,
                "metadata": cls.metadata_suffix,
                "keyword": cls.keyword_suffix,
                "distance": cls.distance_suffix,
            },

            # All 'label' contained in time_stamp, metadata ...
            # are passed inside cls.clean_string
            column_label_value_normaliser=cls.clean_string,
            column_name_normaliser=cls.sql_clean_string,
            logger=cls.logger,
        )

        # TODO: Ensure that sql_clean_string produce a uniq result for all string outputted by clean_string

    @classmethod
    def get_known_databases(cls) ->  dict[str, dict[str, Any]]:
        return BaseTable.get_known_databases()

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
                    and_(ope.eq(TimeStamps.url, self.url), TimeStamps.label == fstsn),
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

        job_entry = self.to_job_entry()
        metadata_entries = self.to_metadata_entries()
        keyword_entries = self.to_keywords_entries()
        time_stamp_entries = self.to_time_stamps_entries()
        distance_entries = self.to_distances_entries()
        all_entries = [
             job_entry,
             *metadata_entries,
             *keyword_entries,
             *time_stamp_entries,
             *distance_entries,
             ]
        session.add_all(
            all_entries
        )

        self.logger.debug(f"'%s' exported using '%s'. %s entries generated.", self, session, len(all_entries))

    def to_job_entry(self) -> Jobs:
        return Jobs(
            url = self.url,
            title = self.title if self.title else None,
            localisation = self.localisation if self.localisation else None,
            contract = self.contract_type if self.localisation else None,
            field = self.field if self.localisation else None,
            origin = self.get_class_name()
        )

    def to_metadata_entries(self) -> list[Metadata]:
        m_l = []
        for key, value in self.metadata.items():
            metadat_obj = Metadata(
                url=self.url,
                key=key,
                value=value
            )
            m_l.append(metadat_obj)
        return m_l

    def to_keywords_entries(self) -> list[Keywords]:
        k_l = []
        for keyword, occurrence in self.keywords.items():
            key_obj = Keywords(
                url=self.url,
                keyword=keyword,
                occurrence=occurrence if occurrence != -1 else None
            )
            k_l.append(key_obj)
        return k_l

    def to_time_stamps_entries(self) -> list[TimeStamps] :
        t_l = []
        for label, t_struct in self.time_stamps.items():
            time_obj = TimeStamps(
                url=self.url,
                label=label,
                time_stamp=datetime.datetime(
                    t_struct.tm_year, t_struct.tm_mon, t_struct.tm_mday,
                    t_struct.tm_hour, t_struct.tm_min, t_struct.tm_sec
                ),
            )
            t_l.append(time_obj)
        return t_l

    def to_distances_entries(self) -> list[Distances]:
        d_l = []
        for reference_localisation, distance in self.distances.items():
            dist_obj = Distances(
                job_localisation=self.localisation,
                reference_localisation=reference_localisation,
                distance=distance if distance != -1 else None,
            )
            d_l.append(dist_obj)
        return d_l

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
            raise KeyError(f"<database_name> should be in `None` or in {cls.available_databases.keys()}."
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

            for time_stamp_entry in TimeStamps.get_for_job(session, new_jobs.url):
                new_jobs.add_time_stamps(time_stamp_entry.label, time_stamp_entry.time_stamp.timetuple())

            for keywords_entry in Keywords.get_for_job(session, new_jobs.url):
                occurrence = keywords_entry.occurrence
                if occurrence is None:
                    occurrence = -1

                new_jobs.add_keyword_count(keywords_entry.keyword, occurrence)

            for distances_entry in Distances.get_job_associated_distances(session, new_jobs.localisation):
                distance = distances_entry.distance
                if distance is None:
                    distance = -1

                new_jobs.add_distance_to(distances_entry.reference_localisation, distance)

            for metadata_entry in Metadata.get_for_job(session, new_jobs.url):
                new_jobs.add_metadata(metadata_entry.key, metadata_entry.value)

            loaded_jobs.append(new_jobs)
        return loaded_jobs

    # --- --- Imports --- ---
    # --- --- Utils --- ---
    _sql_string_to_operators = {
        "A": and_,
        "&": and_,
        "O": or_,
        "|": or_,
        "!": not_,
        "N": not_,
        "": None
    }

    _sql_string_sep = "::"

    @classmethod
    def get_sql_string_to_comparison_operators(cls):
        return STRING_TO_COMPARISON_WRAPPERS

    @classmethod
    def get_sql_string_to_logic_operators(cls):
        return STRING_TO_LOGICAL_WRAPPERS

    @classmethod
    def sql_clean_string(cls, string: str) -> str:
        return cls.clean_string(string).lower()

    # --- --- Utils --- ---

