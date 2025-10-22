from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column
from sqlalchemy.orm import declarative_base
import os
from sqlalchemy.orm import Session, Query
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

    def get_existing_self(self, session: Session) -> 'None | BaseTableForJobScrapper':
        primary_keys = self.get_pk_columns()
        if not primary_keys:
            return None

        return session.query(self.__class__).filter_by(**self.to_pk_dict()).first()

    @classmethod
    def get_column_map(cls) -> dict[str, Column]:
        """
        Return a dictionary mapping column names to their SQLAlchemy column objects.
        Example: {"id": Jobs.id, "title": Jobs.title, ...}
        """
        return {column.name: column for column in cls.__table__.columns}

    @classmethod
    def get_columns(cls):
        return cls.__table__.columns.keys()

    @classmethod
    def to_dict(cls):
        return {c: getattr(cls, c) for c in cls.get_columns()}

    @classmethod
    def flat(cls, sep="\t") -> str:
        return f"{sep}".join(sorted([f"{key}={value}" for key, value in cls.to_dict().items()]))

    @classmethod
    def get_pk_columns(cls) -> list[str]:
        """
        Return the list of primary key column names for a SQLAlchemy model class.
        """
        if cls.__abstract__:
            return []

        mapper = inspect(cls)
        return [column.key for column in mapper.primary_key]

    @classmethod
    def to_pk_dict(cls):
        return {c: getattr(cls, c) for c in cls.get_pk_columns()}

    @classmethod
    def flat_pk(cls, sep="\t") -> str:
        return f"{sep}".join(sorted([f"{key}={value}" for key, value in cls.to_pk_dict().items()]))

    @classmethod
    def get_non_pk_columns(cls):
        return [col for col in cls.__table__.columns.keys() if col not in cls.get_pk_columns()]

    @classmethod
    def to_non_pk_dict(cls):
        return {c: getattr(cls, c) for c in cls.get_non_pk_columns()}

    @classmethod
    def flat_non_pk(cls, sep="\t") -> str:
        return f"{sep}".join(sorted([f"{key}={value}" for key, value in cls.to_non_pk_dict().items()]))

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
