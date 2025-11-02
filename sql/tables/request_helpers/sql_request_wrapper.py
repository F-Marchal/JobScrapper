# pylint: disable=E0611
from logging import Logger
from typing import Callable, Type

from sqlalchemy import ColumnElement, Result

# pylint: disable=E0611
from sqlalchemy.orm import Query, Session

from sql.filters.filter_generator import FilterGenerator, FilterPart
from sql.tables import BaseTable


class SQLRequestWrapper:
    """Class that helps with the generation of sql queries."""

    def __init__(
        self,
        suffixes: dict[str, str] | None = None,
        column_name_cleaner: Callable[[str], str] = lambda string: string,
        logger: None | Logger = None,
    ):
        """
        :param suffixes: A dictionary of string, string that define suffixes to add to generated columns' name.
        :param column_name_cleaner: A callable that clean generated columns' name.
        :param logger: A logger objet
        """
        self.logger: None | Logger = logger
        self.suffixes: dict[str, str] = {}
        self.column_name_cleaner: Callable[[str], str] = column_name_cleaner

        if suffixes:
            self.set_suffixes(**suffixes)

    @classmethod
    def sql_display_query(cls, query: Query) -> None:
        """
        Display a Query result in the terminal.
        """
        first = True
        for row in query.all():
            if first:
                print(row.mapping.keys())
                first = False
            print(row)

    @classmethod
    def sql_display_result(cls, result: Result, sep="\t") -> None:
        """
        Display a Result in the terminal.
        """
        print(sep.join(result.keys()))
        for lines in result:
            print(sep.join([str(l) for l in lines]))

    @classmethod
    def compile_query(cls, query: Query) -> str:
        """
        Compile a query object to a string.
        """
        return str(
            query.statement.compile(compile_kwargs={"literal_binds": True})
        )

    def set_suffixes(self, **suffixes: str):
        """Set suffixes inside self.suffixes. suffix_name=suffix"""
        for suffix_name, suffix in suffixes.items():
            self.suffixes[suffix_name] = suffix

    def get_suffix(self, suffix_name: str) -> str:
        """Returns a suffix name contained inside self.suffixes. if this suffix does not exist : returns ''."""
        if suffix_name in self.suffixes:
            return self.suffixes[suffix_name]
        return ""

    def sql_execute_query(self, session: Session, query: Query) -> Result:
        """Execute a query object on a session and log the Query"""
        if self.logger:
            self.logger.debug("SQL run  : \n%s", self.compile_query(query))
        return session.execute(query)

    def build_request(
        self,
        session: Session,
    ) -> Query:
        """Build wrapper's request"""
        raise NotImplementedError

    def quick_filter_generator(
        self,
        table: Type[BaseTable],
        column_creator: Callable[[str], ColumnElement] | None = None,
        columns: list[str] | None = None,
        fill_none_columns: bool = True,
    ) -> FilterGenerator:
        """Quicly generate a FilterGenerator for a Table."""
        if columns is None:
            if fill_none_columns:
                columns = list(table.get_columns_using_sql_name().keys())
            else:
                columns = []

        fp = FilterPart.list_init(
            table.get_columns_using_sql_name(),
            *columns,
            generate_column_using=column_creator,
            logger=self.logger,
        )

        return FilterGenerator(fp)
