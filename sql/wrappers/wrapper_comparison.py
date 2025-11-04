import re
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import Column, not_
from sqlalchemy.sql import operators as ope
from sqlalchemy.sql.elements import ColumnElement

from .wrapper_clause_element import ClauseElementWrapper


class ComparisonWrapper(ClauseElementWrapper):
    """Wrapper for comparison operators (==, !=, ilike, etc.)"""

    def __init__(
        self,
        op: Callable[[Column, Any], ColumnElement],
        help_: str,
        symbols: list[str],
        types: list[Callable[[str], Any]],
    ):
        """
        :param op: a callable object that can be used in a query.filter()
        :param help_:  A string that give information about the operation done by self.op
        :param symbols: A symbol that represent the operation done by self.op
        :param types: A list of type / cast function that can turn string into
        """
        super().__init__(op, help_, symbols)
        self.types: list[Callable[[str], Any]] = types

    @property
    def op(self) -> Callable[[Column, Any], ColumnElement]:
        return self._op

    @op.setter
    def op(self, operator: Callable[[Column, Any], ColumnElement]):
        self._op = operator

    def cast(self, value: str):
        """Cast a value using cast functions in self.types."""
        if not self.types:
            raise ValueError(
                f"Can not cast '{value}'. No type available in <self.types>"
            )

        cast_succeed = False
        i = 0
        errors = []
        true_value = None
        while i < len(self.types) and not cast_succeed:
            try:
                true_value = self._cast(value, self.types[i])
                cast_succeed = True
            except ValueError as new_e:
                errors.append(new_e)
            finally:
                i += 1

        if cast_succeed:
            return true_value

        raise ValueError(
            f"Unable to cast '{value}', {len(self.types)} methods tested : \n- "
            + "\n- ".join([str(e) for e in errors])
        )

    @staticmethod
    def _cast(value: str, cast_funct: Callable):
        return cast_funct(value)

    @staticmethod
    def ilike_to_regex(pattern: str) -> str:
        """
        Convert SQL/ilike regex to re regex.
        % -> .*
        _ -> .
        """
        regex = ""
        for char in pattern:
            if char == "%":
                regex += ".*"
            elif char == "_":
                regex += "."
            else:
                regex += re.escape(char)
        return f"^{regex}$"


def to_datetime_ymd(string: str):
    """Transform a string to a datetime object using "%Y-%m-%d" format"""
    return datetime.strptime(string, "%Y-%m-%d")


def to_datetime_ymd_hms(string: str):
    """Transform a string to a datetime object using "%Y-%m-%d %H:%M:%S" format"""
    return datetime.strptime(string, "%Y-%m-%d %H:%M:%S")


def to_datetime(string: str):
    """Transform a string to a datetime object using "%Y-%m-%d %H:%M:%S" or "%Y-%m-%d" format"""
    try:
        return to_datetime_ymd(string)
    except ValueError:
        return to_datetime_ymd_hms(string)


EQUAL_WRAPPER = ComparisonWrapper(
    op=ope.eq,
    help_="Column value is equal to <value>",
    symbols=["=="],
    types=[int, float, to_datetime, str],
)

NOT_EQUAL_WRAPPER = ComparisonWrapper(
    op=ope.ne,
    help_="Column value is not equal to <value>",
    symbols=["!="],
    types=[int, float, to_datetime, str],
)

GREATER_WRAPPER = ComparisonWrapper(
    op=ope.gt,
    help_="Column value is greater than <value>",
    symbols=[">"],
    types=[int, float, to_datetime, str],
)

GREATER_EQUAL_WRAPPER = ComparisonWrapper(
    op=ope.ge,
    help_="Column value is greater or equal to <value>",
    symbols=[">="],
    types=[int, float, to_datetime, str],
)

LESSER_WRAPPER = ComparisonWrapper(
    op=ope.lt,
    help_="Column value is lesser than <value>",
    symbols=["<"],
    types=[int, float, to_datetime, str],
)

LESSER_EQUAL_WRAPPER = ComparisonWrapper(
    op=ope.le,
    help_="Column value is lesser or equal to <value>",
    symbols=["<="],
    types=[int, float, to_datetime, str],
)

INSIDE_WRAPPER = ComparisonWrapper(
    op=lambda column, pattern: column.ilike(pattern),
    help_="Column value is inside your <string> (eg. 'pha' is inside 'Alpha'). Case sensitive.",
    symbols=["<-", "Contains"],  # regroup in/out direction as symbols
    types=[str],
)

NOT_INSIDE_WRAPPER = ComparisonWrapper(
    op=lambda column, pattern: not_(column.ilike(pattern)),
    help_="Column value is not inside your <string> (eg. 'b' is not inside 'Alpha'). Case sensitive.",
    symbols=["x-", "~Contains"],  # regroup not in/out
    types=[str],
)

COMPARISON_WRAPPERS = [
    EQUAL_WRAPPER,
    NOT_EQUAL_WRAPPER,
    GREATER_WRAPPER,
    GREATER_EQUAL_WRAPPER,
    LESSER_WRAPPER,
    LESSER_EQUAL_WRAPPER,
    INSIDE_WRAPPER,
    NOT_INSIDE_WRAPPER,
]
STRING_TO_COMPARISON_WRAPPERS: dict[str, ComparisonWrapper] = {
    s: cw for cw in COMPARISON_WRAPPERS for s in cw.symbols
}
