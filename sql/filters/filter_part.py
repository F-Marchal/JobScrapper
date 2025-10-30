from logging import Logger
from sql.wrappers.wrapper_logical import LogicalWrapper, STRING_TO_LOGICAL_WRAPPERS
from sql.wrappers.wrapper_comparison import ComparisonWrapper, STRING_TO_COMPARISON_WRAPPERS
from sqlalchemy.sql.elements import Label, ColumnElement
from typing import Any, Optional, Callable


class FilterPart:
    """
    Uses LogicalWrapper and ComparisonWrapper to generate command from
    a string. The goal of this class is to be used as a program / user
    interface inside ScrapperSQLightCore
    """
    format_help = (
        "1. [Column name] --> Display the column in the result"
        "\n2. [Column name]::[Comparator (==, <=, ilike, ...)]::[Value]"
        " --> Display the column and filter results"
        "\n3. [Operator (&, |, ^, |~, ...)]::[Column name]::[Comparator (==, <=, ilike, ...)]::[Value] "
        "--> Display the column and filter results"
        "\n4. [Parenthesis (')', '(', ')(')]::[Operator (&, |, ^, |~, ...)]::[Column name]::"
        "[Comparator (==, <=, ilike, ...)]::[Value] "
        " --> Display the column and filter results"
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
    ) -> list['FilterPart']:
        """
        initialize one FilterPart per string in *strings
        :param string_to_columns: A dictionary {string : ColumnElement}
        :param strings: a list of string formated as in cls.format_help
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
            string_formater: Callable[[str], str]=lambda string: string,

            separator: str="::",
            logger: Logger | None = None,
            generate_column_using: Callable[[str], ColumnElement] | None = None,

    ):
        """
        :param unformatted_string: A string formated  as in cls.format_help
        :param string_to_columns: A dictionary {str : ColumnElement}
        :param string_formater: : A callable that ensure correct string formatting for column name usage.
        :param separator: used in unformatted_string as separator for each field
        :param logger: A logger to display execution information
        :param generate_column_using: A command that allow column generation when a string
         is not in string_to_columns. Will modify string_to_columns.
        """

        # Attributes without properties:
        self.generate_column_using: Callable[[str], Label] | None = generate_column_using
        self.logger: Logger | None = logger
        self.string_formater = string_formater
        self.string_to_columns: dict[str, ColumnElement] = string_to_columns
        self.unformatted_string: str = unformatted_string

        # Attributes with indirect setter:
        self.start_parenthesis: bool = False
        self.close_parenthesis: bool = False

        # Attributes with properties:
        self.logic_operator = None
        self.comp_operator = None
        self.comp_value = None
        self.column = None

        split_string = unformatted_string.split(separator)
        substring_nb = len(split_string)

        if substring_nb <= 0 or substring_nb == 2:
            if substring_nb == 2:
                if self.logger: self.logger.error(
                    "Invalid format : '%s'. Only the first parti will be used (as column name).\n"
                    "%s",
                    self.format_help,
                )
                self.str_column = split_string[0]
            return

        if substring_nb == 1:
            column = split_string[0]
            self.str_column = column

        elif substring_nb == 3:
            column, cond, value = split_string
            self.column = column
            self.comp_operator = cond
            self.comp_value = value

        elif substring_nb == 4:
            logic, column, cond, value = split_string
            self.logic_operator = logic
            self.column = column
            self.comp_operator = cond
            self.comp_value = value

        if substring_nb == 5:
            parenthesis, logic, column, cond, value = split_string
            self.str_column = column
            self.comp_operator = cond
            self.comp_value = value
            self.logic_operator = logic
            self.set_parenthesis(parenthesis)

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
        A new column can be generated. This will update self.string_to_columns"""
        if column_name is None:
            self._column = None
            return

        true_column_name = self.string_formater(column_name)


        if true_column_name not in self.string_to_columns:
            try:
                self._generate_new_column(column_name)
                self.str_column = column_name
            except AttributeError:
                print("BOOM", self.logger)
                if self.logger: self.logger.error(
                    "Can not process '%s' (column='%s'). Invalid format. Please use one of"
                    " %s",
                    self.unformatted_string, true_column_name, self.string_to_columns.keys()
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
            raise AttributeError(f"self.generate_column_using is None. Can not generate a new column.")

        col_obj = self.generate_column_using(true_name)
        self.string_to_columns[true_name] = col_obj

    @property
    def column(self) -> None | ColumnElement:
        """Column object attached to self."""
        return self._column

    @column.setter
    def column(self, column_name: str):
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

    def parse_string_comp(self, s_condition: str, fall_back_string="==") -> ComparisonWrapper:
        """Transform a string <s_condition> to a ComparisonWrapper using  self.get_string_to_comparison_operators()"""
        string_to_comp = self.get_string_to_comparison_operators()

        if fall_back_string not in string_to_comp:
            raise KeyError(
                f"Invalid fall_back comparison string : {fall_back_string} not in {string_to_comp.keys()} !")

        if s_condition not in string_to_comp:
            if self.logger: self.logger.error(
                "Can not use '%s' as a comparison opperator in '%s'. This condition will be replaced by '%s'. "
                "Please use one of %s.",
                s_condition,
                self.unformatted_string,
                fall_back_string,
                string_to_comp.keys()
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
        If val is None, a fallback wrapper will be selected base on parse_string_logic()'s fall_back_string."""
        if isinstance(val, LogicalWrapper):
            true_val = val
        else:
            true_val = self.parse_string_logic(val)

        self._logic_operator: LogicalWrapper = true_val

    def parse_string_logic(self, s_condition: str | None, fall_back_string="&") -> LogicalWrapper:
        """Transform a string <s_condition> to a ComparisonWrapper using  self.get_string_to_logic_operators()"""
        string_to_logic = self.get_string_to_logic_operators()

        if fall_back_string not in string_to_logic:
            raise KeyError(f"Invalid fall_back logic string : {fall_back_string} not in {string_to_logic.keys()} !")

        if s_condition is None or s_condition not in string_to_logic:
            if self.logger and s_condition is not None: self.logger.warning(
                "Can not use '%s' as a logic opperator in '%s'. This condition will be replaced by '%s'. "
                "Please use one of %s.",
                s_condition,
                self.unformatted_string,
                fall_back_string,
                string_to_logic.keys()
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
    def comp_value(self, value: str):
        """Sets the value used by comp_operator to compare column value"""
        self._comp_value = value

    def parse_string_value(self, val: str, cond_wrap: ComparisonWrapper) -> Any | None:
        """Try to transform a string (<val>) with a ComparisonWrapper <cond_wrap> to type that
        <cond_wrap> can use."""
        try:
            return cond_wrap.cast(val)
        except ValueError as e:
            if self.logger: self.logger.error(
                "Can not cast '%s' from '%s'. The column (%s) will be shown but no condition will be applied."
                "\n%s",
                val, self.unformatted_string, self.str_column, e
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
        if string == "":
            return
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
            if self.logger : self.logger.error(
                "Can parse parenthesis ('%s') in '%s'",
                string, self.unformatted_string
            )
            return
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