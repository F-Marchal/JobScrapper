from logging import Logger
from typing import Any, Callable, Generator, Type

from sqlalchemy import Column, ColumnElement, Result, case, func

# pylint: disable=E0611
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql import operators as ope

from sql.filters.filter_generator import FilterGenerator, FilterPart
from sql.tables import BaseTable


class SQLRequestWrapper:
    """Class that helps with the generation of sql queries.
    This class should be used for queries that require the
    creation of new columns "on the fly" to extract values from
    lookup table.

    | foreign id | label | value |
    |:----------:|:-----:|:-----:|
    |      1     | alpha |   4   |
    |      1     |  beta |   5   |
    |      2     | gamma |   1   |
    |      2     |  beta |   15  |
    |      3     | alpha |   42  |

    ==> (assuming prefix = ' #')

    | id | alpha # | gamma # |
    |:--:|:-------:|:-------:|
    |  1 |    4    |   null  |
    |  2 |   null  |    15   |
    |  3 |    42   |   null  |

    Attrs :
    - <suffixes> can be used to store strings that help differentiate column generated
        (e.g : '#', 'km' ...).
    - <column_name_normaliser> can be used in order to control the format of the generated column.
        In the previous example we can use `lambda string: string.title()` to obtain 'Alpha #' and
        'Gamma #' as column name
    - <column_label_value_normaliser> can be used in order to control the transition from column name
        to element in table.label. As an example the user can pass 'Alpha #' as column name. In this casse
        it might be a good idea to have `column_label_value_normaliser=lambda string: string.lower.strip(' #')`
        in order to ensure that the string passed will match the label
    """

    # --- --- Attrs --- ---
    def __init__(
        self,
        suffixes: dict[str, str] | None = None,
        column_name_normaliser: Callable[[str], str] = lambda string: string,
        column_label_value_normaliser: Callable[
            [str], str
        ] = lambda string: string,
        logger: None | Logger = None,
    ):
        """
        :param suffixes: A dictionary of string, string that define suffixes to add to generated columns' name.
        :param column_name_normaliser: A callable that normalise the column name gave by the user when a new
        column should be created by build_request. See also : FilterPart.string_formater
        :param column_label_value_normaliser: Normalise a string passed inside a FilterPart to match a value
         that might be contained inside a column during the creation of new columns during <build_request>.
        :param logger: A logger objet
        """
        self.logger: None | Logger = logger
        self._suffixes: dict[str, str] = {}
        self.column_name_normaliser: Callable[[str], str] = (
            column_name_normaliser
        )
        self.column_label_value_normaliser = column_label_value_normaliser

        if suffixes:
            self.set_suffixes(**suffixes)

    @property
    def suffixes(self):
        """Returns a copy of self._suffixes"""
        return self._suffixes.copy()

    def set_suffixes(self, **suffixes: str):
        """Set suffixes inside self.suffixes. suffix_name=suffix"""
        for suffix_name, suffix in suffixes.items():
            self._suffixes[suffix_name] = suffix

    def get_suffix(self, suffix_name: str) -> str:
        """Returns a suffix name contained inside self.suffixes. if this suffix does not exist : returns ''."""
        if suffix_name in self.suffixes:
            return self._suffixes[suffix_name]
        return ""

    # --- --- Attrs --- ---
    # --- --- utils --- ---
    @classmethod
    def result_to_flat_file_generator(
        cls, result: Result, sep="\t"
    ) -> Generator[str, None, None]:
        """
        Returns a generator of string that describe how
        the content of the query :
        "col1 col2 col3"
        "val1 val2 val3"
        "val4 val5 val6"
        ...
        """
        yield sep.join(result.keys())
        for lines in result:
            yield sep.join([str(l) for l in lines])

    @classmethod
    def compile_query(cls, query: Query) -> str:
        """
        Compile a query object to a string.
        """
        return str(
            query.statement.compile(compile_kwargs={"literal_binds": True})
        )

    # --- --- utils --- ---
    # --- --- main body --- ---
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
        fill_none_columns: bool = False,
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
            string_formater=self.column_name_normaliser,
        )

        return FilterGenerator(fp)

    def quick_column_creator(
        self,
        label_col: Column,
        value_col: Column,
        else_value: Any = None,
        suffix_name: str = "",
    ) -> Callable[[str], ColumnElement]:
        """
        Quicly generate a Callable[[str], ColumnElement] that try to match a value
        in the label column with a string normalised with <column_label_value_normaliser>
        in order to generate a ColumnElement

        :param label_col: The column that contain a number of label ('first_sighting', 'last_sighting', 'distance_to')
        :param value_col: The column that contains the value of interset
        :param else_value: value used if the match fail for an element (default=null)
        :param suffix_name: A suffix name contained (or not) in self.suffixes. This suffix will be added
            to the label to generate the label of the ColumnElement.
        :return:
        """
        selected_suffix = self.get_suffix(suffix_name)
        return lambda col_name: func.max(
            case(
                (
                    ope.eq(
                        label_col, self.column_label_value_normaliser(col_name)
                    ),
                    value_col,
                ),
                else_=else_value,
            )
        ).label(col_name.removesuffix(selected_suffix) + selected_suffix)
        # Ugly way to ensure that the suffix is at the ↑
        # end of the label with no repetition          ↑

    # --- --- main body --- ---
