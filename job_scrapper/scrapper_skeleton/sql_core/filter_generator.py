
from sqlalchemy.dialects import sqlite
from sqlalchemy.sql.elements import ClauseElement, ColumnElement
from sqlalchemy import or_
from sqlalchemy.orm import Query
from .filter_part import FilterPart


class FilterGenerator:
    def __init__(self, commands: list[FilterPart], ):
        self.filters: None | ClauseElement = None
        self.columns: list[ColumnElement] = []
        self._parse_init(commands)


    @staticmethod
    def clause_element_to_string(command: ClauseElement) -> str:
        return str(command.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))

    @staticmethod
    def query_to_string(query: Query) -> str:
        return str(query.statement.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))

    def _parse_init(
            self,
            commands: list['FilterPart'],
    ) -> None:
        if self.filters:
            raise ValueError(f"Can not call <_make_command> more than one time. ({self})")
        result, _ = self._make_command(commands)
        self.filters = result

    def _make_command(
            self,
            commands: list['FilterPart'],
            i: int = 0
    ) -> tuple[ClauseElement, int]:
        prev_command = None
        first_command = True
        close_parenthesis = False

        while i < len(commands) and not close_parenthesis:
            cf: FilterPart = commands[i]
            if not cf:
                i += 1
                continue

            col = cf.get_column_obj()
            self.columns.append(col)

            if not cf.comp_operator:
                i += 1
                continue

            if col is None:
                if cf.logger: cf.logger.error(
                    "Unknown colum : '%s' from '%s'. %s",
                    cf.str_column, cf.unformatted_string, cf.string_to_columns.keys(),
                )

            elif not first_command and cf.start_parenthesis:
                new_element, new_i = self._make_command(
                    commands,
                    i
                )
                prev_command = cf.logic_operator(prev_command, new_element)
                i = new_i
                continue


            elif not first_command and cf.logic_operator:
                prev_command = cf.logic_operator(
                    prev_command,
                    cf.comp_operator(
                        col,
                        cf.comp_value
                    )
                )

            else:
                prev_command = cf.comp_operator(col, cf.comp_value)
                first_command = False

            i += 1
            close_parenthesis = cf.close_parenthesis

        return prev_command, i

    @property
    def safe_filters(self):
        if self.filters is None:
            return or_(True, True)
        return  self.filters


    def __str__(self):
        if self.filters is not None:
            return self.clause_element_to_string(self.filters)
        return super().__str__()