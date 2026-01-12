import datetime
import os
from contextlib import contextmanager, nullcontext
from typing import Any, ContextManager, Generator, Protocol, Type, Self, Iterator


# pylint: disable=E0611
from sqlalchemy.orm import Query, Session

from job_scrapper.scrapper_skeleton.object_core import ScrapperObjectCore
from job_scrapper.sql.tables import (
    BaseTable,
    Distances,
    Jobs,
    Keywords,
    KeywordVersion,
    KeywordRegex,
    Metadata,
    TimeStamps,
    Places,
)
from job_scrapper.sql.tables.helpers.job_request import JobRequest
from job_scrapper.sql.tables.helpers.keyword_manager import KeywordManager

class SqlSessionFactory(Protocol):
    """Typing class mostly used for ScrapperSQLightCore.get_available_databases"""

    def __call__(
        self, workdir: str | None = None
    ) -> ContextManager[Session]: ...


class ScrapperSQLightCore(ScrapperObjectCore):
    """
    Specialisation of ScrapperObjectCore that allows
    SQL exports and add the creation of an SQL database
    """

    _database_file_name: str = "JobsDatabase"
    _tables: dict[str, Type[BaseTable]] = {
        Jobs.__tablename__: Jobs,
        Metadata.__tablename__: Metadata,
        TimeStamps.__tablename__: TimeStamps,

        Keywords.__tablename__: Keywords,
        KeywordRegex.__tablename__: KeywordRegex,
        KeywordVersion.__tablename__: KeywordVersion,

        Distances.__tablename__: Distances,
        Places.__tablename__: Places,

    }
    first_sighting_time_stamp_name = "First sighting"

    DEFAULT_LOAD_JOB_ENTRY: bool = True
    DEFAULT_LOAD_KEYWORDS: bool = True
    DEFAULT_LOAD_DISTANCES: bool = True
    DEFAULT_LOAD_METADATA: bool = True
    DEFAULT_LOAD_TIME_STAMPS: bool = True

    DEFAULT_OVERWRITE_JOB_ENTRY: bool | set[str] = False,
    DEFAULT_OVERWRITE_KEYWORDS: bool | set[str] = False,
    DEFAULT_OVERWRITE_DISTANCES: bool | set[str] = False,
    DEFAULT_OVERWRITE_METADATA: bool | set[str] = False,
    DEFAULT_OVERWRITE_TIME_STAMPS: bool | set[str] = False,

    @property
    def localisation(self) -> str:
        """Returns the location of this job if job localisation is unknown (None or ""),
        Jobs.DEFAULT_LOCALISATION is returned."""
        localisation =  super(ScrapperSQLightCore, self).localisation
        if not localisation:
            return Jobs.DEFAULT_LOCALISATION
        return localisation

    @localisation.setter
    def localisation(self, value: str | None):
        # Localisation might be used as a column name since it might generate
        # a Places entry.
        self._localisation = self.place_column_name_normaliser(value)

    @classmethod
    def get_job_requester(cls) -> JobRequest:
        """Generate a JobRequest configured to be used
        with a ScrapperSQLightCore"""
        return JobRequest(
            suffixes={
                "time_stamp": cls.time_stamp_suffix,
                "metadata": cls.metadata_suffix,
                "keyword": cls.keyword_suffix,
                "distance": cls.distance_suffix,
            },
            place_name_normaliser=cls.place_column_name_normaliser,
            # All 'label' contained in time_stamp, metadata ...
            # are passed inside cls.clean_string
            column_label_value_normaliser=cls.column_label_value_normaliser,
            column_name_normaliser=cls.column_name_normaliser,
            logger=cls.logger,
        )

    @classmethod
    def get_keyword_manager(cls) -> KeywordManager:
        """Generate a KeywordManager configured to be used
        with a ScrapperSQLightCore"""
        return KeywordManager(
            logger=cls.logger,
        )


    @classmethod
    def get_known_databases(cls) -> dict[str, dict[str, Any]]:
        """Returns BaseTable.get_known_databases()"""
        return BaseTable.get_known_databases()

    @classmethod
    def get_all_tables(cls) -> dict[str, Type[BaseTable]]:
        """Get a dict of tables used by Jobs during sql export / import."""
        return cls._tables.copy()

    @classmethod
    def get_table(cls, table_name: str) -> Type[BaseTable]:
        """Get a table contained inside <get_all_tables>."""
        return cls.get_all_tables()[table_name]

    def __init__(self,
            *args,
             workdir: str | None = None,
             database_name: str | None = None,
             force_session: Session | None = None,

             use_db_init_time_stamp: bool = False,

             load_job_entry: bool | None = None,
             load_keywords: bool | None = None,
             load_distances: bool | None = None,
             load_metadata: bool | None = None,
             load_time_stamps: bool | None = None,

             overwrite_job_entry: bool | set[str] | None = None,
             overwrite_keywords: bool | set[str] | None = None,
             overwrite_distances: bool | set[str] | None = None,
             overwrite_metadata: bool | set[str] | None = None,
             overwrite_time_stamps: bool | set[str] | None = None,

            **kwargs
        ):
        """See ScrapperObjectCore __init__ method.
        This extension will seek first_sighting_time_stamp_name in
        the database and add it to self.time_stamps"""
        super().__init__(*args, **kwargs)
        if load_job_entry is None:
            load_job_entry = self.DEFAULT_LOAD_JOB_ENTRY
        if load_keywords is None:
            load_keywords = self.DEFAULT_LOAD_KEYWORDS
        if load_distances is None:
            load_distances = self.DEFAULT_LOAD_DISTANCES
        if load_metadata is None:
            load_metadata = self.DEFAULT_LOAD_METADATA
        if load_time_stamps is None:
            load_time_stamps = self.DEFAULT_LOAD_TIME_STAMPS

        if overwrite_job_entry is None:
            overwrite_job_entry = self.DEFAULT_OVERWRITE_JOB_ENTRY
        if overwrite_keywords is None:
            overwrite_keywords = self.DEFAULT_OVERWRITE_KEYWORDS
        if overwrite_distances is None:
            overwrite_distances = self.DEFAULT_OVERWRITE_DISTANCES
        if overwrite_metadata is None:
            overwrite_metadata = self.DEFAULT_OVERWRITE_METADATA
        if overwrite_time_stamps is None:
            overwrite_time_stamps = self.DEFAULT_OVERWRITE_TIME_STAMPS

        self._loaded_from = (workdir, database_name)
        session_ctx = (
            self.get_sql_session(workdir=workdir, database_name=database_name)
            if force_session is None
            else nullcontext(force_session)
        )
        with session_ctx as session:
            if load_job_entry:
                self.load_job_entry_from_db(session, overwrite=overwrite_job_entry)

            if load_keywords:
                self.load_keywords_from_db(session, overwrite=overwrite_keywords)

            if load_distances:
                self.load_distances_from_db(session, overwrite=overwrite_distances)

            if load_metadata:
                self.load_metadata_from_db(session, overwrite=overwrite_metadata)

            if load_time_stamps:
                self.load_time_stamps_from_db(
                    session,
                    overwrite=overwrite_time_stamps,
                    use_db_init_time_stamp=use_db_init_time_stamp
                )

        # Ensure fstsn exist
        fstsn = self.first_sighting_time_stamp_name
        if not self.time_stamps_exist(fstsn):
            first_sighting = self.retrieve_time_stamps(
                self.init_time_stamp_name
            )
            self.add_time_stamps(fstsn, first_sighting)

    @property
    def loaded_from(self) -> tuple[str | None, str  | None]:
        return self._loaded_from

    @classmethod
    @contextmanager
    def get_maindb_session(
        cls, workdir: str | None = None
    ) -> Generator[Session, None, None]:
        """Get a session on a Jobs database."""
        path = cls.get_maindb_path(workdir)
        with Jobs.get_session(database_path=path, logger=cls.logger) as session:
            yield session

    @classmethod
    @contextmanager
    def get_archive_session(
        cls, workdir: str | None = None
    ) -> Generator[Session, None, None]:
        """Get a session on an archive Jobs database."""
        path = cls.get_archive_path(workdir)
        with Jobs.get_session(database_path=path, logger=cls.logger) as session:
            yield session

    @classmethod
    def get_available_databases(
        cls,
    ) -> dict[str, SqlSessionFactory]:
        """Returns a dict that contains generic methods that generate
        a session to a Job database."""
        return {
            "maindb": cls.get_maindb_session,
            "archive": cls.get_archive_session,
        }
    DEFAULT_DATABASE = "maindb"

    @classmethod
    @contextmanager
    def get_sql_session(
            cls,
            workdir: str | None = None,
            database_name: str | None = None
    ) -> Generator[Session, None, None]:
        """Give a session on the targeted database."""
        available_databases = cls.get_available_databases()
        database_session_command: SqlSessionFactory | None = None

        if database_name is None:
            database_name = cls.DEFAULT_DATABASE

        if database_name in available_databases:
            database_session_command = available_databases[database_name]

        else:
            raise KeyError(
                f"<database_name> should be in `None` or in {available_databases.keys()}."
                f" Got '{database_name}'"
            )

        if database_session_command is None:
            raise ValueError(
                "Internal error, <database_session_command> should not be None at this point."
                f"locals={locals()}"
            )

        with database_session_command(workdir=workdir) as session:
            yield session

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

        if file_path[-len(ext) :] != ext:
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
    def sql_export(
            self,
            session: Session,
            keywords_ver: dict[str, KeywordVersion] | None = None
    ):
        """
        Export a maximum all field inside the selected database.
        Use self.get_[database]_session to obtain a session

        :param session: A session opened on a database
        :param keywords_ver: A dictionary {keyword=KeywordVersion}
            to ensure that Keywords entries generated by <to_keywords_entries>
            uses the correct KeywordVersion
        """
        self.logger.debug("Exporting '%s' using '%s'", self, session)
        if keywords_ver is None:
            keywords_ver = {}


        # Main entries
        place_entry = self.to_place_entry(session)
        job_entry = self.to_job_entry()
        metadata_entries = self.to_metadata_entries()
        time_stamp_entries = self.to_time_stamps_entries()
        distance_entries = self.to_distances_entries()
        key_ver_entries = self.to_keywords_entries(**keywords_ver)
        if key_ver_entries:
            keyword_ver_entries, keyword_entries = zip(*key_ver_entries)
        else:
            keyword_ver_entries = []
            keyword_entries = []

        # Ensure Place entry existence (mandatory to export job_entry)


        #
        all_entries = [
            place_entry,
            job_entry,
            *metadata_entries,
            *keyword_ver_entries,
            *keyword_entries,
            *time_stamp_entries,
            *distance_entries,
        ]
        session.add_all(all_entries)

        self.logger.debug(
            "'%s' exported using '%s'. %s entries generated.",
            self,
            session,
            len(all_entries),
        )

    def to_place_entry(
            self,
            session: Session,
    ) -> Places:
        """Turn self.localisation to a Place entry.
        If the localisation is known, the place object
        is extracted from the database. Else, a new one is
        generated with `longitude=None` and `latitude=None`."""
        existing_entry = Places.get_job_place(
            session,
            self.localisation
        )

        if existing_entry is not None:
            return existing_entry

        return Places.get_default_entry(self.localisation) # if self.localisation else None

    def to_job_entry(self) -> Jobs:
        """Generate a Jobs entry that represent self"""
        return Jobs(
            url=self.url,
            title=self.title if self.title else None,
            localisation=self.localisation, # if self.localisation else None
            contract=self.contract_type if self.localisation else None,
            field=self.field if self.localisation else None,
            origin=self.get_standardised_class_name(),
        )

    def to_metadata_entries(self) -> list[Metadata]:
        """Generate all associate Metadata entries"""
        m_l = []
        for key, value in self.metadata.items():
            metadat_obj = Metadata(url=self.url, key=key, value=value)
            m_l.append(metadat_obj)
        return m_l

    def to_keywords_entries(
            self,
            **keywords_ver: KeywordVersion
    ) -> list[tuple[KeywordVersion, Keywords]]:
        """Generate all associate Keywords entries

        use keyword=KeywordVersion to ensure that generated Keywords entries
        uses the correct KeywordVersion
        """
        k_l = []
        for keyword, occurrence in self.keywords.items():
            if keyword in keywords_ver:
                version_obj = keywords_ver[keyword]
            else:
                version_obj = KeywordVersion(
                    version=-1,
                    keyword=keyword
                )

            key_obj = Keywords(
                url=self.url,
                keyword=keyword,
                version = version_obj.version,
                occurrence=occurrence if occurrence != -1 else None,
            )
            k_l.append((version_obj, key_obj))

        return k_l

    def to_time_stamps_entries(self) -> list[TimeStamps]:
        """Generate all associate TimeStamps entries"""
        t_l = []
        for label, t_struct in self.time_stamps.items():
            time_obj = TimeStamps(
                url=self.url,
                label=label,
                time_stamp=datetime.datetime(
                    t_struct.tm_year,
                    t_struct.tm_mon,
                    t_struct.tm_mday,
                    t_struct.tm_hour,
                    t_struct.tm_min,
                    t_struct.tm_sec,
                ),
            )
            t_l.append(time_obj)
        return t_l

    def to_distances_entries(self) -> list[Distances]:
        """Generate all associate Distances entries"""
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
    def _sql_batch_export(
            cls,
            session: Session,
            *jobs: "ScrapperSQLightCore",
            keywords_ver: dict[str, KeywordVersion] | None = None
    ):
        for job in jobs:
            job.sql_export(session, keywords_ver=keywords_ver)

    @classmethod
    def sql_batch_export(
        cls,
        *jobs: "ScrapperSQLightCore",
        database_name: str | None = None,
        workdir: None | str = None,
        keywords_ver: dict[str, KeywordVersion] | None = None
    ):
        """
        Export an array of jobs in the selected database
        :param jobs: A number of ScrapperObjectCore
        :param database_name: The targeted database (see  cls.get_available_databases())
        :param workdir: A directory where the database will be written.
        :param keywords_ver: A dictionary {keyword=KeywordVersion}
                to ensure that Keywords entries generated by <to_keywords_entries>
                uses the correct KeywordVersion
        """

        with cls.get_sql_session(workdir=workdir, database_name=database_name) as session:
            cls.logger.debug("Exporting %s job offers...", len(jobs))
            cls._sql_batch_export(session, *jobs, keywords_ver=keywords_ver)
            cls.logger.debug("%s job offer exported !", len(jobs))

    # --- --- Exports --- ---
    # --- --- Imports --- ---
    @classmethod
    def sql_import_jobs(
        cls,
        session: Session,
        request: Query[Jobs] | None = None,
        use_db_init_time_stamp: bool = True,
    ) -> Iterator[Self]:
        """
        Generate a list of ScrapperSQLightCore (or current subclass) from a query.
        If this query is None Jobs.get_all(session) is used.
        """
        if not request:
            request = Jobs.get_all(session)

        for job_entry in request:
            cls.logger.debug(f"Loading {job_entry.url}...")

            yield cls.load_from_db(url=job_entry.url, session=session, use_db_init_time_stamp=use_db_init_time_stamp)

    @classmethod
    def load_from_db(
            cls,
            url: str,
            session: Session,
            use_db_init_time_stamp: bool = True,
    ):
        return cls(
            url=url,
            force_session=session,

            load_job_entry=True,
            load_keywords=True,
            load_distances=True,
            load_metadata=True,
            load_time_stamps=True,

            overwrite_job_entry=True,
            overwrite_keywords=True,
            overwrite_distances=True,
            overwrite_metadata=True,
            overwrite_time_stamps=True,

            use_db_init_time_stamp=use_db_init_time_stamp,
        )


    def load_job_entry_from_db(self, session: Session, overwrite: set[str] | bool = False):
        entries = session.query(Jobs).where(Jobs.url == self.url).all()
        if not entries:
            return

        self.load_job_entry(entries[0], overwrite=overwrite)

    def load_job_entry(
            self,
            job_entry: Jobs,
            overwrite: set[str] | bool = False,
            safe: bool = True
    ):
        if safe and job_entry.url != self.url:
            raise KeyError(
                "Can not load 'job_entry' ({job_entry}) since job_entry.url != self.url and safe=True. \n"
                "('{job_entry.url}' != '{self.url}')."
            )

        if (overwrite is True or "title" in overwrite) or self.title in ("",):
            self.title = job_entry.title

        if (overwrite is True or "localisation" in overwrite) or self.localisation in ("", Jobs.DEFAULT_LOCALISATION):
            self.localisation = job_entry.localisation

        if (overwrite is True or "contract_type" in overwrite) or self.contract_type in ("",):
            self.contract_type = job_entry.contract

        if (overwrite is True or "field" in overwrite) or self.field in ("",):
            self.field = job_entry.field

    def load_time_stamps_from_db(
            self,
            session: Session,
            overwrite: set[str] | bool = False,
            use_db_init_time_stamp: bool = False,
    ):
        for time_stamp_entry in TimeStamps.get_for_job(
            session, self.url
        ):
            self.load_time_stamp_entry(time_stamp_entry, overwrite, use_db_init_time_stamp=use_db_init_time_stamp)

    def load_time_stamp_entry(
            self,
            time_stamp_entry: TimeStamps,
            overwrite: set[str] | bool = False,
            use_db_init_time_stamp: bool = False,
    ):
        # If self.time_stamps_exist then we might overwrite it. Can we ?
        if (overwrite is False or (isinstance(overwrite, set) and time_stamp_entry.label not in overwrite)) and self.time_stamps_exist(time_stamp_entry.label):
            return

        if self.init_time_stamp_name == time_stamp_entry.label and not use_db_init_time_stamp:
            # This entry should not be overwritten.
            return

        self.add_time_stamps(
            time_stamp_entry.label,
            time_stamp_entry.time_stamp.timetuple(),
        )

    def load_keywords_from_db(self, session: Session, overwrite: set[str] | bool = False,):
        for keywords_entry in Keywords.get_for_job(session, self.url):
            self.load_keyword_entry(keywords_entry, overwrite)

    def load_keyword_entry(self, keywords_entry: Keywords, overwrite: set[str] | bool = False,):
        if (
                (overwrite is False or (isinstance(overwrite, set) and keywords_entry.keyword not in overwrite))
                and self.keyword_exist(keywords_entry.keyword)
        ):
            return

        occurrence = keywords_entry.occurrence
        if occurrence is None:
            occurrence = -1

        self.add_keyword_count(keywords_entry.keyword, occurrence)

    def load_distances_from_db(self, session: Session, overwrite: set[str] | bool = False,):
        for distances_entry in Distances.get_job_associated_distances(
            session, self.localisation
        ):
            self.load_distance_entry(distances_entry, overwrite)

    def load_distance_entry(self, distances_entry: Distances, overwrite: set[str] | bool = False,):
        label = distances_entry.reference_localisation
        if (overwrite is False or (isinstance(overwrite, set) and not label in overwrite)) and self.distance_to_exist(label):
            return

        distance = distances_entry.distance
        if distance is None:
            distance = -1
        self.add_distance_to(
            label, distance
        )

    def load_metadata_from_db(self, session: Session, overwrite: set[str] | bool = False,):
        for metadata_entry in Metadata.get_for_job(session, self.url):
            self.load_metadata_entry(metadata_entry, overwrite)

    def load_metadata_entry(self, metadata_entry: Metadata, overwrite: set[str] | bool = False,):
        if (overwrite is False or (isinstance(overwrite, set) and metadata_entry.key not in overwrite)) and self.metadata_exist(metadata_entry.key):
            return
        self.add_metadata(metadata_entry.key, metadata_entry.value)

    # --- --- Remove from db --- ---
    def self_delete_from_db(self, session: Session):
        # This expects that Jobs have delete cascade on
        # TimeStamps, keywords, metadata ...
        session.delete(self.to_job_entry())


    def archive(
        self,
        initial_session: Session,
        target_session: Session,


    ):
       self.to_job_entry().archive(
            initial_database=initial_session,
            target_database=target_session,
        )


    # --- --- Remove from db --- ---
    # --- --- Utils --- ---
    @classmethod
    def column_name_normaliser(cls, string: str) -> str:
        """Method that parse a string to turn it into a string
        that can be used as a column name during request using
        <cls.get_job_requester()>
        """
        string2 = cls.clean_string(string)
        if string2:
            return string2.lower()
        return ""

    @classmethod
    def column_label_value_normaliser(cls, string: str) -> str:
        """A method that parse a string to turn it into a string that
        can be contained in the 'label' column of a lookup table
        related to Jobs.
        E.g : Keywords.keyword, Metadata.key ... (When those table are filled
        using self.sql_export).

        Currently, this a wrapper for cls.clean_string that returns "" when
        cls.clean_string returns None.
        """
        string2 = cls.clean_string(string)
        if string2:
            return string2
        return ""

    @classmethod
    def place_column_name_normaliser(cls, string: str) -> str:
        return Places.format_localisation(cls.clean_string(string))

    # --- --- Utils --- ---
