from mypyc.ir.rtypes import void_rtype
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
import os
from sqlalchemy.orm import Session, Query
from sqlalchemy.engine import Engine
import traceback
from sqlalchemy.inspection import inspect
from contextlib import contextmanager
from logging import Logger
from typing import Any
_Base = declarative_base()

class BaseTableForJobScrapper(_Base):
    __abstract__ = True
    _databases: dict[str, dict[str, Any]] = {}

    # --- --- Engines, sessions and database management --- ---
    @classmethod
    def get_known_databases(cls) ->  dict[str, dict[str, Any]]:
        if not cls._databases:
            return {}
        return {path: dict_.copy() for path, dict_ in cls._databases.items()}

    @classmethod
    def _get_engine(cls, database_path: str):
        os.makedirs(os.path.dirname(database_path), exist_ok=True)
        engine = create_engine(f"sqlite:///{database_path}", echo=False)
        return engine

    @classmethod
    @contextmanager
    def get_session(cls, database_path: str, logger: Logger | None = None):
        database_path = os.path.abspath(database_path)
        if database_path not in cls._databases:
            if logger: logger.debug("Database engine initialisation in '%s' ...", database_path)
            engine = cls._get_engine(database_path)
            session_maker = sessionmaker(bind=engine)
            cls.create_all(engine)
            cls._databases[database_path] = {
                "engine": engine,
                "session_maker": session_maker,
                "initialised": True
            }

        session_maker = cls._databases[database_path]["session_maker"]
        session = session_maker()
        if logger: logger.debug("Database session opened ('%s') for '%s'.", session, database_path)
        try:
            with session.no_autoflush: # Remove autoflush in order to keep avoid sanitise flush.
                yield session
                if session.new:
                    cls._sanitise_and_commit(session, logger)
                session.commit()

        except Exception as error:
            session.rollback()
            if logger: logger.error("Error while '%s' was opened ! Rollback all modifications. \n%s", session,  traceback.format_exc())
            raise error

        finally:
            if logger: logger.debug("Database session closed ('%s') for '%s'. "
                                    "Everything went fine.", session, database_path)
            session.close()

    @classmethod
    def _sanitise_and_commit(cls, session: Session, logger: Logger | None = None):
        viewed_entries = {

        }
        if logger: logger.debug("Session sanitation (%s) of %s elements", session, len(session.new))
        insertion = 0
        ignored = 0
        existing_counter = 0
        updates = 0
        for entries in session.new:
            existing = entries.get_existing_self(session)
            table_name = entries.__tablename__
            flat_pk: str = entries.flat_pk()

            if existing:
                if existing == entries:
                    if logger: logger.debug("Ignoring '%s' export since it has the exact same content as an existing entry (%s)"
                                 "\n(%s)\nExisting : %s\n=="
                                 "\n'New' : %s\n", entries, existing, session, existing.flat(), entries.flat())

                    session.expunge(entries)
                    existing_counter += 1
                    continue

                if logger: logger.debug(
                    f"'%s' already exist in database.\n(%s)\n"
                    f"Updating existing entry : "
                    f"\nExisting : \t%s\n-->"
                    f"\nNew : \t%s\n", entries, session, existing.flat(), entries.flat()
                )
                session.expunge(entries)
                updates += 1
                for column in entries.get_non_pk_columns():
                    setattr(existing, column, getattr(entries, column))
                continue

            if table_name not in viewed_entries:
                viewed_entries[table_name] = {}

            if flat_pk in viewed_entries[table_name]:
                previous = viewed_entries[table_name][flat_pk]

                if previous == entries:
                    if logger: logger.debug("Ignoring '%s' export since it has the exact same content as"
                                 " another new entry '%s'\n(%s)"
                                 "\nPrevious : %s\n=="
                                 "\nCurrent : %s\n", entries, previous, session, previous.flat(), entries.flat())

                else:
                    if logger: logger.debug("Ignoring '%s' export since it has the same primary key(s) as a previous"
                                 "entry ('%s').\n(%s)"
                                 "\nPrevious : %s\n!="
                                 "\nCurrent : %s\n", entries, previous, session, previous.flat(), entries.flat())
                ignored += 1
                session.expunge(entries)
                continue

            viewed_entries[table_name][flat_pk] = entries
            insertion += 1

        if logger: logger.debug("Session sanitation (%s) done :"
                     "\n\tinsertion : %s"
                     "\n\tignored : %s"
                     "\n\texisting : %s"
                     "\n\tupdates : %s", session, insertion, ignored, existing_counter, updates)






    @classmethod
    def create_all(cls, engine) -> None:
        """
        Generate all table (if they do not exist)
        """
        cls.metadata.create_all(engine)

    # --- --- Engines, sessions and database management --- ---
    # --- --- Descriptions --- ---
    def __eq__(self, other):
        if not isinstance(other, BaseTableForJobScrapper):
            return NotImplemented

        return other.to_dict() == self.to_dict()

    def exists(self, session: Session) -> bool:
        if self.get_existing_self(session):
            return True
        return False

    def get_existing_self(self, session: Session) -> 'None | Keywords':
        primary_keys = self.get_pk_columns()
        if not primary_keys:
            return None

        return session.query(self.__class__).filter_by(**self.to_pk_dict()).first()


    @classmethod
    def get_columns(cls):
        return cls.__table__.columns.keys()

    def to_dict(self):
        return {c: getattr(self, c) for c in self.get_columns()}

    def flat(self, sep="\t") -> str:
        return f"{sep}".join(sorted([f"{key}={value}" for key, value in self.to_dict().items()]))

    @classmethod
    def get_pk_columns(cls) -> list[str]:
        """
        Return the list of primary key column names for a SQLAlchemy model class.
        """
        if cls.__abstract__:
            return []

        mapper = inspect(cls)
        return [column.key for column in mapper.primary_key]

    def to_pk_dict(self):
        return {c: getattr(self, c) for c in self.get_pk_columns()}

    def flat_pk(self, sep="\t") -> str:
        return f"{sep}".join(sorted([f"{key}={value}" for key, value in self.to_pk_dict().items()]))

    @classmethod
    def get_non_pk_columns(cls):
        return [col for col in cls.__table__.columns.keys() if col not in cls.get_pk_columns()]

    def to_non_pk_dict(self):
        return {c: getattr(self, c) for c in self.get_non_pk_columns()}

    def flat_non_pk(self, sep="\t") -> str:
        return f"{sep}".join(sorted([f"{key}={value}" for key, value in self.to_non_pk_dict().items()]))

    # --- --- Descriptions --- ---
    # --- --- Standard requests --- ---
    @classmethod
    def get_all(cls, session: Session) -> Query:
        """
        Returns a query object that contains all session's entries.
        You can chain filter after that.
        Example :
            query = Table.get_all(session).filter(Table.field == "value")
            all_items = Table.get_all(session).all()
        """
        return session.query(cls)

    # --- --- Standard requests --- ---

class Jobs(BaseTableForJobScrapper):
    __abstract__ = False
    __tablename__ = "jobs"

    # Table columns
    contract = Column(String, nullable=False)
    field = Column(String, nullable=False)
    localisation = Column(String, nullable=False)
    origin = Column(String, nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, primary_key=True, nullable=False)

    # time_stamp = Column(Date, nullable=False)

    # Table relationships
    # Relations dynamiques
    metadata_entries = relationship(
        "Metadata",
        back_populates="main_entry",
        cascade="all, delete-orphan",
        lazy='dynamic' # Gives a query object instead of a list when job = session.get(Jobs, "url_du_job") ; job.metadata_entries
    )
    keywords_entries = relationship(
        "Keywords",
        back_populates="main_entry",
        cascade="all, delete-orphan",
        lazy='dynamic'
    )
    timestamps_entries = relationship(
        "TimeStamps",
        back_populates="main_entry",
        cascade="all, delete-orphan",
        lazy='dynamic'
    )

    # Ease requests
    # distances_from_job = relationship(
    #    "Distances",
    #    primaryjoin="Jobs.localisation==Distances.job_localisation",
    #    back_populates="job",
    #    lazy='dynamic',  # important pour filtrer avec .filter()
    #    viewonly=True
    #)


class Metadata(BaseTableForJobScrapper):
    __abstract__ = False
    __tablename__ = "metadata"

    # Table columns
    url = Column(String, ForeignKey(f"{Jobs.__tablename__}.url", ondelete="CASCADE"), primary_key=True)
    key = Column(String, primary_key=True, nullable=False)
    value = Column(String, nullable=False)

    # Table relationships
    main_entry = relationship("Jobs", back_populates="metadata_entries", passive_deletes=True)

    @classmethod
    def get_associated_metadata(cls, session: Session, url: str) -> list:
        return session.query(cls).filter_by(url=url).all()

class Keywords(BaseTableForJobScrapper):
    __abstract__ = False
    __tablename__ = "keywords"

    url = Column(String, ForeignKey(f"{Jobs.__tablename__}.url", ondelete="CASCADE"), primary_key=True)
    keyword = Column(String, primary_key=True, nullable=False)
    occurrence = Column(Integer)

    main_entry = relationship("Jobs", back_populates="keywords_entries", passive_deletes=True)

    @classmethod
    def get_associated_keywords(cls, session: Session, url: str) -> list:
        return session.query(cls).filter_by(url=url).all()


class TimeStamps(BaseTableForJobScrapper):
    __abstract__ = False
    __tablename__ = "timestamps"

    url = Column(String, ForeignKey(f"{Jobs.__tablename__}.url", ondelete="CASCADE"), primary_key=True)
    label = Column(String, primary_key=True, nullable=False)
    time_stamp =  Column(DateTime, nullable=False)

    main_entry = relationship("Jobs", back_populates="timestamps_entries", passive_deletes=True)

    @classmethod
    def get_associated_time_stamps(cls, session: Session, url: str) -> list:
        return session.query(cls).filter_by(url=url).all()


class Distances(BaseTableForJobScrapper):
    __abstract__ = False
    __tablename__ = "distances"

    reference_localisation = Column(String, primary_key=True, nullable=False)
    job_localisation = Column(String, primary_key=True, nullable=False)
    distance = Column(Float)

    @classmethod
    def get_associated_distances(cls, session: Session, job_localisation: str) -> list:
        return session.query(cls).filter_by(job_localisation=job_localisation).all()




    # job = relationship(
    #    "Jobs",
    #    primaryjoin=f"Jobs.localisation==Distances.job_localisation",
    #    back_populates="distances_from_job",
    #    viewonly=True
    # )
