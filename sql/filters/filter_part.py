from logging import Logger
from typing import Any, Callable

from sqlalchemy.sql.elements import ColumnElement

from sql.wrappers.wrapper_comparison import (
    STRING_TO_COMPARISON_WRAPPERS,
    ComparisonWrapper,
)
from sql.wrappers.wrapper_logical import (
    STRING_TO_LOGICAL_WRAPPERS,
    LogicalWrapper,
)


# pylint: disable=R0902,R0913,R0917
# This is the amount of attribute that I need
# and the number of parameter that I need to initialise those attributes
class FilterPart:
    """
    Uses LogicalWrapper and ComparisonWrapper to generate command from
    a string. The goal of this class is to be used as a program / user
    interface inside ScrapperSQLightCore
    """

    @staticmethod
    def get_format_help() -> str:
        """Return a complete helps to configure strings used to initialise a FilterPart"""
        comparators = "\n\t".join(
            f"'{str_op}': {w.help} ({', '.join(t.__name__ for t in w.types)})"
            for str_op, w in STRING_TO_COMPARISON_WRAPPERS.items()
        )

        logical = "\n\t".join(
            f"'{str_op}': {w.help} "
            for str_op, w in STRING_TO_LOGICAL_WRAPPERS.items()
        )
        return (
            "Four format are available. All format will add [Column name] to the result.\n"
            "1. [Column name] ; \n"
            "2. [Column name]::[Comparator]::[Value] ; \n"
            "3. [Operator]::[Column name]::[Comparator]::[Value] ; \n"
            "4. [Parenthesis]::[Operator]::[Column name]::[Comparator]::[Value] ; \n\n"
            "With : \n"        
             "1. [Column name] : The name of the targeted column ; \n"
            f"2. [Comparator] : filters the entries to include only those that satisfy the "
            f"condition defined by the [Comparator] and [Value]."
            f"Can be one of the following comparator : \n\t{comparators} \n"
             "3. [Value] : Any string that can be converted into a type compatible with [Comparator] ; \n"
            f"4. [Operator] : Defines how the previous condition interacts with the current : \n\t{logical} ; \n"
             "5. [Parenthesis] : Allows you to group conditions together to control their evaluation"
            "use one of '(', ')', ')(' ; \n"
        )

    @classmethod
    def list_init(
        cls,
        string_to_columns: dict[str, ColumnElement],
        *strings: str,
        separator: str = "::",
        logger: Logger | None = None,
        generate_column_using: Callable[[str], ColumnElement] | None = None,
        string_formater: Callable[[str], str] = lambda string: string,
    ) -> list["FilterPart"]:
        """
        initialize one FilterPart per string in *strings
        :param string_to_columns: A dictionary {string : ColumnElement}
        :param strings: a list of string formated as in cls.get_format_help()
        :param separator: used in strings
        :param logger: A logger to display execution information
        :param generate_column_using: A command that allow column generation when a string
         is not in string_to_columns. Will modify string_to_columns.
        :param string_formater: A callable that ensure correct string formatting for column name usage.
        """
        all_items = []
        for item in strings:
            all_items.append(
                cls(
                    item,
                    separator=separator,
                    logger=logger,
                    string_to_columns=string_to_columns,
                    generate_column_using=generate_column_using,
                    string_formater=string_formater,
                )
            )
        return all_items

    def __init__(
        self,
        unformatted_string: str,
        string_to_columns: dict[str, ColumnElement],
        string_formater: Callable[[str], str] = lambda string: string,
        separator: str = "::",
        logger: Logger | None = None,
        generate_column_using: Callable[[str], ColumnElement] | None = None,
    ):
        """
        :param unformatted_string: A string formated  as in cls.get_format_help()
        :param string_to_columns: A dictionary {str : ColumnElement}
        :param string_formater: : A callable that ensure correct string formatting for column name usage.
        :param separator: used in unformatted_string as separator for each field
        :param logger: A logger to display execution information
        :param generate_column_using: A command that allow column generation when a column name
         is not inside. string_to_columns. Will modify string_to_columns.
        """

        # Attributes without properties:
        self.generate_column_using: Callable[[str], ColumnElement] | None = (
            generate_column_using
        )
        self.logger: Logger | None = logger
        self.string_formater = string_formater
        self.string_to_columns: dict[str, ColumnElement] = string_to_columns
        self.unformatted_string: str = unformatted_string

        attribute_dict = self.parse_unformatted_string(
            unformatted_string, separator=separator
        )

        # Attributes with properties:
        self.logic_operator = attribute_dict["logic_operator"]
        self.comp_operator = attribute_dict["comp_operator"]
        self.comp_value = attribute_dict["comp_value"]
        self.column = None
        self.str_column = attribute_dict["str_column"]

        # Attributes with indirect setter:
        self.start_parenthesis: bool = False
        self.close_parenthesis: bool = False
        self.set_parenthesis(attribute_dict["parenthesis"])

    def parse_unformatted_string(
        self, unformatted_string: str, separator: str = "::"
    ) -> dict[str, Any]:
        """Parse an unformatted string and turn it into a dict of attributes."""

        result: dict[str, Any] = {
            "str_column": None,
            "comp_operator": None,
            "comp_value": None,
            "logic_operator": None,
            "parenthesis": "",
        }

        split_string = unformatted_string.split(separator)
        substring_nb = len(split_string)

        match split_string:
            case [column]:
                result["str_column"] = column

            case [column, cond, value]:
                result["str_column"] = column
                result["comp_operator"] = cond
                result["comp_value"] = value

            case [logic, column, cond, value]:
                result["logic_operator"] = logic
                result["str_column"] = column
                result["comp_operator"] = cond
                result["comp_value"] = value

            case [parenthesis, logic, column, cond, value]:
                result["parenthesis"] = parenthesis
                result["logic_operator"] = logic
                result["str_column"] = column
                result["comp_operator"] = cond
                result["comp_value"] = value

            case [column, _]:
                if substring_nb == 2:
                    if self.logger:
                        self.logger.error(
                            "Invalid format : '%s'. Only the first parti will be used (as column name).\n"
                            "%s",
                            unformatted_string,
                            self.get_format_help(),
                        )
                    result["str_column"] = column

            case [_]:
                result["str_column"] = None

        return result

    #  --- --- Attributes --- ---
    # --- Column related ---
    @property
    def str_column(self) -> str | None:
        """Unformatted column name."""
        return self._str_column

    @str_column.setter
    def str_column(self, column_name: str | None):
        """Set str_column using a string (column_name).
        This string is used to determine which column in self.string_to_columns
        should be used as self.column. if  self._generate_new_column is not None,
        A new column can be generated. This will update self.string_to_columns
        """
        if column_name is None:
            self._column = None
            return

        true_column_name = self.string_formater(column_name)

        if true_column_name not in self.string_to_columns:
            try:
                self._generate_new_column(column_name)
                self.str_column = column_name
            except AttributeError as ae:
                print("BOOM", self.logger)
                if self.logger:
                    self.logger.error(
                        "Can not process '%s' (column='%s'). Invalid format. Please use one of"
                        " %s\nColumn generator message : %s",
                        self.unformatted_string,
                        true_column_name,
                        list(self.string_to_columns.keys()),
                        ae
                    )
                self._str_column = ""
                self._column = None

        else:
            self._str_column = true_column_name
            self._column = self.string_to_columns[self._str_column]

    def _generate_new_column(self, true_name: str):
        """Generate a new column using self.generate_column_using"""
        true_name = self.string_formater(true_name)
        if self.generate_column_using is None:
            raise AttributeError(
                "self.generate_column_using is None. Can not generate a new column."
            )

        col_obj = self.generate_column_using(true_name)
        self.string_to_columns[true_name] = col_obj

    @property
    def column(self) -> None | ColumnElement:
        """Column object attached to self."""
        return self._column

    @column.setter
    def column(self, column_name: str | None):
        """Set column obect attached to self using a string and  self.string_to_columns"""
        self.str_column = column_name

    # --- Column related ---
    # --- Wrapper related ---
    @property
    def comp_operator(self) -> None | ComparisonWrapper:
        """Return ComparisonWrapper attached to self"""
        return self._comp_operator

    @comp_operator.setter
    def comp_operator(self, val: str | ComparisonWrapper | None):
        """Set ComparisonWrapper attached to self using a string '>=', '==', ...,
        a ComparisonWrapper or None"""
        if isinstance(val, ComparisonWrapper):
            true_val = val
        elif val is None:
            true_val = None
        else:
            true_val = self.parse_string_comp(val)

        self._comp_operator: ComparisonWrapper | None = true_val

    def parse_string_comp(
        self, s_condition: str, fall_back_string="=="
    ) -> ComparisonWrapper:
        """Transform a string <s_condition> to a ComparisonWrapper using  self.get_string_to_comparison_operators()"""
        string_to_comp = self.get_string_to_comparison_operators()

        if fall_back_string not in string_to_comp:
            raise KeyError(
                f"Invalid fall_back comparison string : {fall_back_string} not in {string_to_comp.keys()} !"
            )

        if s_condition not in string_to_comp:
            if self.logger:
                self.logger.error(
                    "Can not use '%s' as a comparison opperator in '%s'. This condition will be replaced by '%s'. "
                    "Please use one of %s.",
                    s_condition,
                    self.unformatted_string,
                    fall_back_string,
                    string_to_comp.keys(),
                )
            s_condition = fall_back_string

        return string_to_comp[s_condition]

    @property
    def logic_operator(self) -> LogicalWrapper:
        """Returns LogicalWrapper attached to self"""
        return self._logic_operator

    @logic_operator.setter
    def logic_operator(self, val: str | LogicalWrapper | None):
        """set LogicalWrapper attached to self using a string
        ('&', '|', ...) or a LogicalWrapper. This attribute can not
        be None due to FilterGenerator requirements.
        If val is None, a fallback wrapper will be selected base on parse_string_logic()'s fall_back_string.
        """
        if isinstance(val, LogicalWrapper):
            true_val = val
        else:
            true_val = self.parse_string_logic(val)

        self._logic_operator: LogicalWrapper = true_val

    def parse_string_logic(
        self, s_condition: str | None, fall_back_string="&"
    ) -> LogicalWrapper:
        """Transform a string <s_condition> to a ComparisonWrapper using  self.get_string_to_logic_operators()"""
        string_to_logic = self.get_string_to_logic_operators()

        if fall_back_string not in string_to_logic:
            raise KeyError(
                f"Invalid fall_back logic string : {fall_back_string} not in {string_to_logic.keys()} !"
            )

        if s_condition is None or s_condition not in string_to_logic:
            if self.logger and s_condition is not None:
                self.logger.warning(
                    "Can not use '%s' as a logic opperator in '%s'. This condition will be replaced by '%s'. "
                    "Please use one of %s.",
                    s_condition,
                    self.unformatted_string,
                    fall_back_string,
                    string_to_logic.keys(),
                )
            s_condition = fall_back_string

        return string_to_logic[s_condition]

    # --- Wrapper related ---
    # --- Value related ---
    @property
    def comp_value(self) -> Any:
        """Returns the value used by comp_operator to compare column value"""
        if self._comp_operator is None:
            return None
        return self.parse_string_value(self._comp_value, self._comp_operator)

    @comp_value.setter
    def comp_value(self, value: str | None):
        """Sets the value used by comp_operator to compare column value"""
        self._comp_value = value

    def parse_string_value(
        self, val: str | None, cond_wrap: ComparisonWrapper
    ) -> Any | None:
        """Try to transform a string (<val>) with a ComparisonWrapper <cond_wrap> to type that
        <cond_wrap> can use."""
        if val is None:
            return val

        try:
            return cond_wrap.cast(val)
        except ValueError as e:
            if self.logger:
                self.logger.error(
                    "Can not cast '%s' from '%s'. The column (%s) will be shown but no condition will be applied."
                    "\n%s",
                    val,
                    self.unformatted_string,
                    self.str_column,
                    e,
                )
            self.comp_operator = None
            return None

    # --- Value related ---
    # --- Parenthesis ---
    def set_parenthesis(self, string: str) -> None:
        """Set parenthesis attached to this part.
        Use :
        - ')' to close parenthesis
        - '(' to open parenthesis
        - ')(' to close last parenthesis and open a new one"""
        if not string:
            self.start_parenthesis = False
            self.close_parenthesis = False
        elif string == ")":
            self.start_parenthesis = False
            self.close_parenthesis = True
        elif string == "(":
            self.start_parenthesis = True
            self.close_parenthesis = False
        elif string == ")(":
            self.start_parenthesis = True
            self.close_parenthesis = True
        else:
            if self.logger:
                self.logger.error(
                    "Can not parse parenthesis ('%s') in '%s'",
                    string,
                    self.unformatted_string,
                )

    # --- Parenthesis ---
    # --- --- Utils --- ---
    @classmethod
    def get_string_to_comparison_operators(cls) -> dict[str, ComparisonWrapper]:
        """Returns STRING_TO_COMPARISON_WRAPPERS, a dictionary that associate strings with
        ComparisonWrapper"""
        return STRING_TO_COMPARISON_WRAPPERS

    @classmethod
    def get_string_to_logic_operators(cls) -> dict[str, LogicalWrapper]:
        """Returns STRING_TO_LOGICAL_WRAPPERS  a dictionary that associate strings with
        LogicalWrapper"""
        return STRING_TO_LOGICAL_WRAPPERS

    def __str__(self):
        return self.unformatted_string

    def __bool__(self):
        if self.column is not None:
            return True
        return False

    # --- --- Utils --- ---
