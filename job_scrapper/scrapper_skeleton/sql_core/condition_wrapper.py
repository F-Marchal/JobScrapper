from sqlalchemy.sql import operators as ope
from sqlalchemy import and_, or_, Column
from datetime import datetime
from typing import Callable, Any
from sqlalchemy.sql.elements import ClauseElement

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


class ConditionWrapper:
    """
    An object that encapsulate a callable object that can be used
    in a query.filter()
    """
    def __init__(
            self,
            op: Callable[[Column, Any], ClauseElement],
            help_: str,
            symbol: str,
            types: list[Callable[[str], Any]]
    ):
        """
        :param op: a callable object that can be used in a query.filter()
        :param help_:  A string that give information about the operation done by self.op
        :param symbol: A symbol that represent the operation done by self.op
        :param types: A list of type / cast function that can turn string into
        """
        self.op: Callable[[Column, Any], ClauseElement] = op
        self.help: str = help_
        self.symbol: str = symbol
        self.types: list[Callable[[str], Any]] = types

    def __call__(self, *args, **kwargs):
        """Call self.op and returns results"""
        return self.op(*args, **kwargs)

    def __str__(self):
        """Returns self.symbol"""
        return self.symbol

    def cast(self, value: str):
        """Cast a value using cast functions in self.types."""
        if not self.types:
            raise ValueError(f"Can not cast '{value}'. No type available in <self.types>")

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
        else:
            raise ValueError(
                f"Unable to cast '{value}', {len(self.types)} methods tested : \n- " +
                "\n- ".join([str(e) for e in errors])
            )


    @staticmethod
    def _cast(value: str, cast_funct: Callable):
        return cast_funct(value)

COMPARISON_OPE: list[ConditionWrapper] = [
    ConditionWrapper(
        op=ope.eq,
        help_="Column value is equal to <value>",
        symbol="==",
        types=[int, float, to_datetime, str]
    ),
    ConditionWrapper(
        op=ope.ne,
        help_="Column value is not equal to <value>",
        symbol="!=",
        types=[int, float, to_datetime, str]
    ),
    ConditionWrapper(
        op=ope.gt,
        help_="Column value is greater than <value>",
        symbol=">",
        types=[int, float, to_datetime]
    ),
    ConditionWrapper(
        op=ope.ge,
        help_="Column value is greater or equal to <value>",
        symbol=">=",
        types=[int, float, to_datetime]
    ),
    ConditionWrapper(
        op=ope.lt,
        help_="Column value is lesser than <value>",
        symbol="<",
        types=[int, float, to_datetime]
    ),
    ConditionWrapper(
        op=ope.le,
        help_="Column value is lesser or equal to <value>",
        symbol="<=",
        types=[int, float, to_datetime]
    ),
    ConditionWrapper(
        op=ope.in_op,
        help_="Column value is inside your <string> (eg. 'pha' is inside 'Alpha'). Case Unsensitive.",
        symbol="->",
        types=[str]
    ),
    ConditionWrapper(
        op=ope.notin_op,
        help_="Column value is not inside your <string> (eg. 'b' is not inside 'Alpha'). Case Unsensitive.",
        symbol="-x",
        types=[str]
    ),
    ConditionWrapper(
        op=lambda a, b: ope.in_op(b, a),
        help_="Column value does contain your <pattern>.",
        symbol="<-",
        types=[str]
    ),
    ConditionWrapper(
        op=lambda a, b: ope.notin_op(b, a),
        help_="Column value does not contain your <pattern>.",
        symbol="x-",
        types=[str]
    ),
]
STRING_TO_COMPARISON_OPE: dict[str, ConditionWrapper] = {cw.symbol: cw for cw in COMPARISON_OPE}

LOGICAL_OPE: list[ConditionWrapper] = [
    ConditionWrapper(
        op=and_,
        help_="Logical AND (last and current conditions must be true)",
        symbol="A",
        types=[bool]
    ),
    ConditionWrapper(
        op=and_,
        help_="Logical AND (last and current conditions must be true)",
        symbol="&",
        types=[bool]
    ),
    ConditionWrapper(
        op=or_,
        help_="Logical OR (last or current condition must be true)",
        symbol="O",
        types=[bool]
    ),
    ConditionWrapper(
        op=or_,
        help_="Logical OR (last or current condition must be true)",
        symbol="|",
        types=[bool]
    ),
    # TODO: add And_not
    # TODO: add Or_not
    # TODO: Add XOR
    # ConditionWrapper(
    #    op=not_,
    #    help_="Logical NOT (condition must not be True)",
    #    symbol="!",
    #    types=[bool]
    # ),
    ConditionWrapper(
        op=and_,
        help_="Empty condition (no condition applied)",
        symbol="",
        types=[bool]
    ),

]
STRING_TO_LOGIC_OPE: dict[str, ConditionWrapper] = {cw.symbol: cw for cw in LOGICAL_OPE}