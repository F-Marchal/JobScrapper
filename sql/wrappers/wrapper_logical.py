from typing import Callable

from sqlalchemy import and_, not_, or_
from sqlalchemy.sql.elements import ColumnElement

from .wrapper_clause_element import ClauseElementWrapper


class LogicalWrapper(ClauseElementWrapper):
    """Wrapper for logical operators (and_, or_) taking exactly two conditions."""

    def __init__(
        self,
        op: Callable[..., ColumnElement],
        help_: str,
        symbols: list[str],
    ):
        """
        :param op: a callable object that can be used in a query.filter()
        :param help_:  A string that give information about the operation done by self.op
        :param symbols: A symbol that represent the operation done by self.op
        """
        super().__init__(op, help_, symbols)

    @property
    def op(
        self,
    ) -> Callable[..., ColumnElement]:
        return self._op

    @op.setter
    def op(
        self,
        operator: Callable[..., ColumnElement],
    ):
        self._op = operator


AND_WRAPPER = LogicalWrapper(
    op=and_,
    help_="Logical AND (last and current conditions must be true)",
    symbols=["And", "&"],
)

OR_WRAPPER = LogicalWrapper(
    op=or_,
    help_="Logical OR (last or current condition must be true)",
    symbols=["Or", "|"],
)

XOR_WRAPPER = LogicalWrapper(
    op=lambda first, second: and_(
        or_(first, second), not_(and_(first, second))
    ),
    help_="Logical XOR (Only one of the two should be True)",
    symbols=["Xor", "^"],
)

AND_NOT_WRAPPER = LogicalWrapper(
    op=lambda first, second: and_(first, not_(second)),
    help_="Logical AND NOT (The two conditions should be False)",
    symbols=["And not", "&~"],
)

OR_NOT_WRAPPER = LogicalWrapper(
    op=lambda first, second: or_(first, not_(second)),
    help_="Logical OR NOT (None of the two conditions can be True)",
    symbols=["Or not", "|~"],
)
LOGICAL_WRAPPERS = [
    AND_WRAPPER,
    OR_WRAPPER,
    XOR_WRAPPER,
    AND_NOT_WRAPPER,
    OR_NOT_WRAPPER,
]
STRING_TO_LOGICAL_WRAPPERS: dict[str, LogicalWrapper] = {
    s: cw for cw in LOGICAL_WRAPPERS for s in cw.symbols
}
