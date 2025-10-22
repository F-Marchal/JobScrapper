import os
import datetime
from sqlalchemy import  ColumnElement
from contextlib import contextmanager
from typing import Any, Type

# pylint: disable=E0611
from sqlalchemy.orm import Session, Query
from sqlalchemy import case, func, and_, or_, not_, Result


from ..object_core import ScrapperObjectCore
from .sql_tables import BaseTableForJobScrapper, Jobs, Metadata, TimeStamps, Distances, Keywords
from .filter_generator import FilterPart, FilterGenerator
from .wrapper_comparison import STRING_TO_COMPARISON_WRAPPERS
from .wrapper_logical import STRING_TO_LOGICAL_WRAPPERS
from sqlalchemy.sql import operators as ope

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
        string = cls.clean_string(string)
        string = string.removesuffix(cls.keyword_suffix)
        string = string.removesuffix(cls.distance_suffix)
        string = string.removesuffix(cls.metadata_suffix)
        string = string.removesuffix(cls.time_stamp_suffix)
        return string

    @classmethod
    def sql_request_wrapper(
            cls,
            session: Session,
            columns: list[str] | None = None,
            distances_from: list[str] | None = None,
            keywords: list[str] | None = None,
            metadata: list[str] | None = None,
            time_stamp: list[str] | None = None,
            order_by: list[str] | None = None,

    ) -> Query:
        # Parse inputs
        job_filter = cls._sql_request_wrapper_jobs(columns)
        distance_filter = cls._sql_request_wrapper_distance(distances_from)
        keywords_filter = cls._sql_request_wrapper_keywords(keywords)
        time_filter = cls._sql_request_wrapper_time_stamp(time_stamp)
        metadata_filter = cls._sql_request_wrapper_metadata(metadata)

        all_cols: list[ColumnElement] = [
            *job_filter.columns,
            *distance_filter.columns,
            *keywords_filter.columns,
            *time_filter.columns,
            *metadata_filter.columns,
        ]

        order_by_cols = cls._sql_request_wrapper_order_by(all_cols, order_by)



        query = session.query(
            *all_cols
        ).join(
            Keywords,
            Keywords.url == Jobs.url
        ).join(
            Distances,
            Distances.job_localisation == Jobs.localisation
        ).join(
            TimeStamps,
            TimeStamps.url == Jobs.url
        ).join(
            Metadata,
            Metadata.url == Jobs.url
        ).where(
            job_filter.safe_filters
        ).group_by(
            Jobs.url
        ).having(
            or_(
                distance_filter.safe_filters,
                keywords_filter.safe_filters,
                time_filter.safe_filters,
                metadata_filter.safe_filters
            )
        ).order_by(
            *order_by_cols
        )

        return query


    @classmethod
    def sql_execute_query(cls, session : Session, query: Query) -> Result:
        cls.logger.debug("SQL run  : \n%s", query.statement.compile(compile_kwargs={"literal_binds": True}))
        return session.execute(query)

    @classmethod
    def sql_display_result(cls, result: Result, sep="\t"):
        print(sep.join(result.keys()))
        for lines in result:
            print(sep.join([str(l) for l in lines]))

    @classmethod
    def _sql_request_wrapper_order_by(
            cls,
            all_cols : list[ColumnElement],
            order_by: list[str] | None = None,
    ) -> list[ColumnElement]:
        if order_by is None:
            return []

        order = {cls.sql_clean_string(col_n): i for i, col_n in enumerate(order_by)}
        result = []
        for col in all_cols[:]:
            col_name =  cls.sql_clean_string(col.name)
            if col_name not in order:
                continue

            all_cols.remove(col)
            all_cols.insert(order[col_name], col)
            result.append(col)

        return result


    @classmethod
    def _sql_request_wrapper_jobs(cls, columns: list[str] | None):
        if columns is None:
            columns = Jobs.get_columns()

        fp = FilterPart.list_init(
            Jobs.to_dict(),
            *columns,
            logger=cls.logger,
        )

        return FilterGenerator(fp)
    @classmethod
    def _sql_request_wrapper_distance(cls, distances_from: list[str] | None = None,):
        if distances_from is None:
            distances_from = []
        # TODO: Test that Table.name == cls.sql_clean_string(Table.name)
        gcu = lambda col_name: func.max(
            case(
                (
                    ope.eq(
                        Distances.reference_localisation,
                        cls.sql_clean_string(col_name)
                    ),
                    Distances.distance
                ),
                else_=None
            )
        ).label(col_name + cls.distance_suffix)

        fp = FilterPart.list_init(
            Distances.to_dict(),
            *distances_from,
            generate_column_using=gcu,
            logger=cls.logger,
        )

        return FilterGenerator(fp)

    @classmethod
    def _sql_request_wrapper_keywords(cls, keywords: list[str] | None = None, ):
        if keywords is None:
            keywords = []

        gcu = lambda col_name: func.max(
            case(
                (
                    ope.eq(
                        Keywords.keyword,
                        cls.sql_clean_string(col_name)
                    ),
                    Keywords.occurrence
                ),
                else_=None
            )
        ).label(col_name + cls.keyword_suffix)

        fp = FilterPart.list_init(
            Keywords.to_dict(),
            *keywords,
            generate_column_using=gcu,
            logger=cls.logger,
        )

        return FilterGenerator(fp)

    @classmethod
    def _sql_request_wrapper_time_stamp(cls, time_stamps: list[str] | None = None, ):
        if time_stamps is None:
            time_stamps = []


        gcu = lambda col_name: func.max(
            case(
                (
                    ope.eq(
                        TimeStamps.label,
                        cls.sql_clean_string(col_name)
                    ),
                    TimeStamps.time_stamp
                ),
                else_=None
            )
        ).label(col_name + cls.time_stamp_suffix)

        fp = FilterPart.list_init(
            TimeStamps.to_dict(),
            *time_stamps,
            generate_column_using=gcu,
            logger=cls.logger,
        )

        return FilterGenerator(fp)

    @classmethod
    def _sql_request_wrapper_metadata(cls, metadatas: list[str] | None = None, ):
        if metadatas is None:
            metadatas = []
        gcu = lambda col_name: func.max(
            case(
                (
                    ope.eq(
                        Metadata.key,
                        cls.sql_clean_string(col_name)
                    ),
                    Metadata.value
                ),
                else_=None
            )
        ).label(col_name + cls.metadata_suffix)

        fp = FilterPart.list_init(
            TimeStamps.to_dict(),
            *metadatas,
            generate_column_using=gcu,
            logger=cls.logger,
        )

        return FilterGenerator(fp)


    @classmethod
    def sql_display_query(cls, query):
        first = True
        for row in query.all():
            if first:
                print(row._mapping.keys())
                first = False
            print(row)




    @classmethod
    def _sql_select_columns(cls, database: Type[BaseTableForJobScrapper], *columns):
        c_map = database.get_column_map()
        selected_cols_object = []
        for col in columns:
            if col not in c_map:
                cls.logger.warning(
                    "Can not find '%s' col in '%s'. Please use one of %s.",
                    col, database.__tablename__, c_map.keys()
                )
                continue
            selected_cols_object.append(c_map[col])
        return selected_cols_object

