from typing import Any, Callable

from sqlalchemy import create_engine, literal, select
from sqlalchemy.sql.elements import ColumnElement


class ClauseElementWrapper:
    """
    An object that encapsulate a callable object that can be used
    in a query.filter()
    """

    def __init__(
        self,
        op: Callable[[Any, Any], ColumnElement],
        help_: str,
        symbols: list[str],
    ):
        """
        :param op: a callable object that can be used in a query.filter()
        :param help_:  A string that give information about the operation done by self.op
        :param symbols: A symbol that represent the operation done by self.op
        """
        self.op = op
        self.help: str = help_
        self.symbols: list[str] = symbols

    @property
    def op(self) -> Callable[[Any, Any], ColumnElement]:
        """Returns a callable object that can be used in a query.filter()"""
        return self._op

    @op.setter
    def op(self, operator: Callable[[Any, Any], ColumnElement]):
        self._op = operator

    def __call__(self, *args, **kwargs) -> ColumnElement:
        """Call self.op and returns results"""
        return self.op(*args, **kwargs)

    def __str__(self):
        """Returns self.symbol"""
        return self.symbols[0]

    @classmethod
    def run_operator(
        cls,
        op: Callable[[Any, Any], ColumnElement],
        value1: Any,
        value2: Any,
    ) -> bool:
        """
        Run an Operator using literal values and return the result
        :param op: Any callable object that accept two arguments and returns a ClauseElement
        :param value1: Any value accepted by op
        :param value2: Any value accepted by op
        """
        engine = create_engine("sqlite:///:memory:")
        stmt = select(
            op(literal(value1), literal(value2)),
        )

        with engine.connect() as conn:
            return conn.execute(stmt).scalar_one()

    def run(self, value1: Any, value2: Any) -> bool:
        """
        Run self() using literal values and return the result
        :param value1: Any value accepted by self.op
        :param value2: Any value accepted by self.op
        """
        engine = create_engine("sqlite:///:memory:")
        stmt = select(self(literal(value1), literal(value2)))

        with engine.connect() as conn:
            return conn.execute(stmt).scalar_one()
