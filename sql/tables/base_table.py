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
        """
        Ensure that error will not be raised when an entry is known by the database
        (primary key conflict).
        - Same primary keys added twice : The first one is kept, the second one is ignored
        - Added primary key exist in database : The one contained in the database is updated
            to match the newer one
        :param session: A Session object
        :param logger: An optional logger to display logs.
        """
        viewed_entries: dict[str, dict[str, BaseTableForJobScrapper]] = {

        }

        for d_entries in session.dirty:
            d_table_name = d_entries.__table__
            if d_table_name not in viewed_entries:
                viewed_entries[d_table_name] = {}
            d_flat_pk = d_entries.flat_pk()

            viewed_entries[d_table_name][d_flat_pk] = d_entries

        if logger: logger.debug(
            "Session sanitation (%s) of %s new elements and %s elements modified",
            session,
            len(session.new),
            len(viewed_entries)
        )
        insertion = 0
        ignored = 0
        existing_counter = 0
        updates = len(viewed_entries)
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
                for column in entries.get_non_pk_col_attr_name():
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

        if logger: logger.debug(
            "Session sanitation (%s) done :"
                 "\n\tinsertion : %s"
                 "\n\tignored : %s"
                 "\n\texisting : %s"
                 "\n\tupdates : %s",
                session, insertion, ignored, existing_counter, updates
        )


    @classmethod
    def create_all(cls, engine) -> None:
        """
        Generate all table (if they do not exist)
        """
        cls.metadata.create_all(engine)

    # --- --- Engines, sessions and database management --- ---
    # --- --- Descriptions --- ---
    @staticmethod
    def are_equivalent(
            t1: 'BaseTableForJobScrapper',
            t2: 'BaseTableForJobScrapper',
            strict: bool=False
    ):
        """Says weather two BaseTableForJobScrapper are equivalent (same primary keys).
        Use `strict=True` to compare all columns values.

        THIS DOES NOT PERFORM CLASS TYPE CHECK. TWO DIFFERENT TABLE WITH THE SAME PRIMARY KEYS WILL BE
        CONSIDERED IDENTICAL !!"""
        if strict:
            return t1.to_dict() == t2.to_dict()
        return  t1.to_pk_dict() == t2.to_pk_dict()

    def is_equivalent_to(
            self,
            other: 'BaseTableForJobScrapper',
            strict: bool=False
    ):
        """Says weather another BaseTableForJobScrapper is equivalent to self. (same primary keys).
        Use `strict=True` to compare all columns values and not only the primary keys.

        THIS DOES NOT PERFORM CLASS TYPE CHECK. TWO DIFFERENT TABLE WITH THE SAME PRIMARY KEYS WILL BE
        CONSIDERED IDENTICAL !!"""
        return self.are_equivalent(self, other, strict=strict)


    def __eq__(self, other):
        """Says weather another BaseTableForJobScrapper is equivalent to self. (same primary keys).

        THIS DOES NOT PERFORM CLASS TYPE CHECK. TWO DIFFERENT TABLE WITH THE SAME PRIMARY KEYS WILL BE
        CONSIDERED IDENTICAL !!"""
        if not isinstance(other, BaseTableForJobScrapper):
            return NotImplemented

        return self.is_equivalent_to(other)

    def __str__(self):
        return f"{type(self).__name__}({self.flat(sep='|')})"

    def exists(
            self,
            session: Session,
            strict: bool = False,
            include_session: bool = False,
            include_database: bool = True,
    ) -> bool:
        """Returns True if an equivalent of this entry exist in the database.
        Two entries are equivalent when theirs primary keys are the same.
        If you want to alo compare other keys, use strict=True"""
        eq = self.get_existing_self(
            session,
            strict=strict,
            include_session=include_session,
            include_database=include_database
        )
        if eq is None:
            return False
        if strict:
            return eq == self
        return True


    def get_existing_self(
            self,
            session: Session,
            strict: bool = False,
            include_session: bool = False,
            include_database: bool = True
    ) -> 'None | BaseTableForJobScrapper':
        """
        Returns an entry equivalent to self.
        :param session: A session connected to a database
        :param strict: strict=False only compare primary keys, strict=True ensure full equality (all columns).
        :param include_session: When True, search an equivalent entry inside session.new.
        :param include_database: When True, search an equivalent entry inside session's database.
        :return:
        """
        if include_session is False and include_database is False:
            return None

        if include_session:
            found = None
            for obj in [*session.new, *session.dirty]:
                if self.is_equivalent_to(obj, strict=strict):
                    found = obj

            if found is not None:
                return found

        if include_database:
            if strict:
                keys = self.to_dict()
            else:
                keys = self.to_pk_dict()

            if not keys:
                return None

            return session.query(self.__class__).filter_by(**keys).first()
        return None

    @classmethod
    def get_columns_using_sql_name(cls) -> dict[str, Column]:
        """
        Return a dictionary mapping column names to their SQLAlchemy column objects.
        Example: {"column name in database": Column object, "title": Jobs.title, ...}
        """
        if cls.__abstract__:
            return {}
        return {column.name: column for column in cls.__table__.columns}

    @classmethod
    def get_columns_using_attr_name(cls) -> dict[str, Column]:
        """Returns a dictionary : {table attribute name: Column obj}"""
        if cls.__abstract__:
            return {}

        mapper = inspect(cls)
        results = {}
        for sql_prop in mapper.column_attrs:
            orm_name = sql_prop.key
            results[orm_name] = sql_prop.columns[0]

        return results

    @classmethod
    def get_pk_col_attr_name(cls) -> dict[str, Column]:
        """
        Return the list of primary key column names for a SQLAlchemy model class.
        """
        return {col_name: col for col_name, col in cls.get_columns_using_attr_name().items() if col.primary_key}

    @classmethod
    def get_non_pk_col_attr_name(cls) -> dict[str, Column]:
        """Return a dict that contain <column attribute name> : <Column object that are not primary key>"""
        return {col_name: col for col_name, col in cls.get_columns_using_attr_name().items() if not col.primary_key}


    def to_dict(self) -> dict[str, Any]:
        """Returns a dict  <column attribute name> : <Column value>"""
        tmp = {c: getattr(self, c) for c in self.get_columns_using_attr_name()}
        return tmp

    def flat(self, sep="\t") -> str:
        """Turns an entry to a string that represent each column.
        '<column attribute name>=<Column value>' The order of <column attribute name> is determined
         by a `sorted` function"""
        # Sort keys and join key=value pairs with separator
        d_ = self.to_dict()
        return sep.join([f"{key}={d_[key]}" for key in sorted(d_.keys())])


    def to_pk_dict(self) -> dict[str, Any]:
        """Returns a dict that contain <column attribute name> : <Column object that are primary key>"""
        return {c: getattr(self, c) for c in self.get_pk_col_attr_name()}

    def flat_pk(self, sep="\t") -> str:
        """Turns an entry to a string that represent each column marked as primary key.
        '<column attribute name>=<Column value>' The order of <column attribute name> is determined
         by a `sorted` function"""
        d_ = self.to_pk_dict()
        return sep.join([f"{key}={d_[key]}" for key in sorted(d_.keys())])

    def to_non_pk_dict(self) -> dict[str, Any]:
        """Returns a dict that contain <column attribute name> : <Column object that are not primary key>"""
        return {c: getattr(self, c) for c in self.get_non_pk_col_attr_name()}


    def flat_non_pk(self, sep="\t") -> str:
        """Turn an entry to a string that represent each column not marked as primary key.
        '<column attribute name>=<Column value>' The order of <column attribute name> is determined
         by a `sorted` function"""
        d_ = self.to_non_pk_dict()
        return sep.join([f"{key}={d_[key]}" for key in sorted(d_.keys())])

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
