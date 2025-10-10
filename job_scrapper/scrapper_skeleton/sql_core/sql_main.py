from .sql_core import ScrapperSQLightCore
from .sql_command_constructor import SQLCommandFormater
import re
import datetime

class ScrapperSQLightRunner(ScrapperSQLightCore):
    # --- Main command ---
    @classmethod
    def parse_sql_generate_command_from_list(
            cls,
            table: str,
            column: str,
            *items: str,
            no_condition_allowed: bool = True,
    ):

        legal_names = cls.sql_column_content(table, column, distinct=True)
        pattern = re.compile("|".join(legal_names))
        cls.logger.debug("Parsing : %s", items)

        result = []
        for strings in items:
            pattern_found = re.search(pattern, strings)
            if not pattern_found:
                cls.logger.warning(f"Ignoring unknown {table}.{column}'s value: '%s'\n"
                                   f"Valid values are %s", strings, legal_names)
                continue

            pos1, pos2 = pattern_found.span()

            reference = strings[pos1:pos2]
            if pos1 != 1:
                sql_condition = "OR"

            else:
                if strings[0].upper() in ("&", "A"):
                    sql_condition = "AND"

                elif strings[0].upper() in ("|", "O"):
                    sql_condition = "OR"

                elif strings[0].upper() in ("^", "X"):
                    sql_condition = "XOR"

                else:
                    cls.logger.warning("Unknown condition replaced by OR : '%s'."
                                       "Please ues '&', 'A' (AND), '|', 'O' (OR), '^', 'X' (XOR) ", strings[0])
                    sql_condition = "OR"

            condition = strings[pos2:]

            if condition and no_condition_allowed:
                cls.logger.warning(f"%s.%s does not support condition. Ignoring condition : %s", table, column, strings)
                result.append((reference, None, None, None))
                continue
            if not condition:
                result.append((reference, None, None, None))
                continue

            if condition[0] == "!":
                operator = "<>"
            elif condition[0] in (">", "<", "="):
                operator = condition[0]
            else:
                cls.logger.warning("Ignoring condition ('%s') : "
                                   "Unknown operator ('%s'). (Use '<', '>', '=', '!')", strings, condition[0])
                continue

            if len(condition) == 1:
                cls.logger.warning("Ignoring condition ('%s') : Missing value after '%s'", strings, operator)
                continue

            try:
                value = float(condition[1:])
            except ValueError as error1:
                try:
                    value = cls._parse_datetime(condition[1:])
                except ValueError as error2:
                    cls.logger.warning("Can not parse '%s' : '%s' & '%s'", condition[1:], error1, error2)
                    continue

            result.append((reference, operator, value, sql_condition))

        return result

    @classmethod
    def _sql_generate_command_from_list(
            cls,
            conditions: list[str],
            scf: 'SQLCommandFormater',
            main_table: str,
            main_join_on: str,
            second_table: str,
            second_join_on: str,
            column_to_check: str,
            column_to_keep: str,
            relax: bool = False,
            suffix: str = "_col",
            first_operator_exist: bool = False,
            having_condition: str = "",
            no_condition_allowed: bool = False,
            new_columns: list[str] = None,
    ):

        result = cls.parse_sql_generate_command_from_list(second_table, column_to_check, *conditions,
                                                          no_condition_allowed=no_condition_allowed)
        opened_parenthesis = False
        # Select
        renaming = f"MAX(CASE WHEN {second_table}.{column_to_check} = ? THEN {second_table}.{column_to_keep} END) AS"

        for (reference, operator, value, sql_condition) in result:
            # Select
            reference_column_name = cls.sql_header_compatible_string(f"{reference}{suffix}")

            if new_columns is not None:
                new_columns.append(reference_column_name)
            scf.select_command.append(f'{renaming} {reference_column_name}')

            # Join
            scf.join_arguments.append(reference)
            scf.select_arguments.append(reference)

            if not operator:
                continue

            # Having
            if not first_operator_exist:
                sql_condition = ""
                first_operator_exist = True

            if not opened_parenthesis:
                if having_condition:
                    scf.having_command.append(having_condition)
                scf.having_command.append("(")
                opened_parenthesis = True

            if relax:
                having_command = f"{sql_condition} ({reference_column_name} {operator} ? OR {reference_column_name} IS NULL)"
            else:
                having_command = f"{sql_condition} {reference_column_name} {operator} ?"

            scf.having_command.append(having_command)
            scf.having_arguments.append(value)

        if opened_parenthesis:
            scf.having_command.append(")")

        scf.join_command.extend([
            f"LEFT JOIN {second_table}",
            f"ON {main_table}.{main_join_on} = {second_table}.{second_join_on}",
            f"AND {second_table}.{column_to_check} IN ({', '.join(['?'] * len(result))})"
        ])

        return first_operator_exist

    @classmethod
    def _sql_generate_command_select(
            cls,
            columns: list[str],
            scf: 'SQLCommandFormater',
    ):
        valid_column_name = set(cls.sql_table_column_name(cls.main_table_name))
        if len(columns) != len(set(columns)):
            raise IndexError(f"<columns> isn't allowed to contain any duplicates. {columns}")

        for column_name in columns:
            if column_name not in valid_column_name:
                cls.logger.warning(
                    f"Invalid column name for %s. Column ignored : %s."
                    f"\nValid names are %s", cls.main_table_name, column_name, valid_column_name
                )
                columns.remove(column_name)
                continue

            scf.select_command.append(f"{cls.main_table_name}.{column_name}")

    @classmethod
    def sql_generate_command(
            cls,
            columns: list[str] | None = None,
            distances_from: list[str] | None = None,
            keywords: list[str] | None = None,
            metadata: list[str] | None = None,
            order_by: list[str] | None = None,
            time_stamp: list[str] | None = None,
            distance_relax: bool = False,

            after: datetime.datetime = None,
            before: datetime.datetime = None,

            origin_blacklist: list[str] | None = None,
            origin_whitelist: list[str] | None = None,

            field_blacklist: list[str] | None = None,
            field_whitelist: list[str] | None = None,

            contract_blacklist: list[str] | None = None,
            contract_whitelist: list[str] | None = None,

            title_blacklist: list[str] | None = None,
            title_whitelist: list[str] | None = None,

    ):
        """
        :param list[str] | None  columns: A list of column names. Each selected column will be displayed
            in the final result. By default, all column are displayed.
            (Values returned by sql_table_column_name(cls.main_table_name))
        :param list[str] | None  distances_from:
            Display distances from reference places. Places  can be any place contained
            in the reference_localisation of cls.distance_table_name. You can use them to filter results
            by formatting Them as follows:
            [operator][Place][condition] : Operator should be'&', 'A' (AND), '|', 'O' (OR), '^', 'X' (XOR) ;
            The condition can be '<', '>', '=', '!' followed by a float.
        :param list[str] | None keywords:
            Display keywords occurrence in a job offer. keywords can be any string contained
            in the key of cls.keyword_table_name. You can use them to filter results
            by formatting Them as follows:
            [operator][keywords][condition] : Operator should be'&', 'A' (AND), '|', 'O' (OR), '^', 'X' (XOR) ;
            The condition can be '<', '>', '=', '!' followed by a float.
        :param list[str] | None metadata: Display metadata attached to a job offer. metadata can be any string contained
            in the key of cls.metadata_table_name. You can not use them to filter results.
        :param list[str] | None time_stamp:
            Display time_stamp intel related to job offer.  You can use them to filter results
            by formatting Them as follows:
            [operator][time stamp name][condition] : Operator should be'&', 'A' (AND), '|', 'O' (OR), '^', 'X' (XOR) ;
            The condition can be '<', '>', '=', '!' followed by a date (YYYY-MM-JJ or YYYY-MM-JJ HH:MM:SS).
        :param list[str] | None order_by: List of column name. Fill the 'ORDER BY' statement
        :param bool distance_relax: Do jobs with null values pass all distance filter ?
        :param datetime.datetime after: Only shows job that have last been seen after a date.
        :param datetime.datetime before: Only shows job that have last been seen before a date.
        :param list[str] | None origin_blacklist:
            A list of patterns (use `%` to represent zero or more unknown characters and `_`
            to represent a single unknown character)
            that should **not** be contained in the job's 'origin' field.
        :param list[str] | None origin_whitelist:
            A list of patterns (use `%` to represent zero or more unknown characters and `_`
            to represent a single unknown character)  that **must** be contained in the job's 'origin' field.
        :param list[str] | None field_blacklist:
            A list of patterns (use `%` to represent zero or more unknown characters and `_`
             to represent a single unknown character)  that should **not** appear in the job's 'field' field.
        :param list[str] | None field_whitelist:
            A list of patterns (use `%` to represent zero or more unknown characters and `_`
            to represent a single unknown character)  that **must** appear in the job's 'field' field.
        :param list[str] | None contract_blacklist:
            A list of patterns (use `%` to represent zero or more unknown characters and `_`
            to represent a single unknown character)  that should **not** appear in the job's 'contract' field.
        :param list[str] | None contract_whitelist:
            A list of patterns (use `%` to represent zero or more unknown characters and `_`
             to represent a single unknown character)  that **must** appear in the job's 'contract' field.
        :param list[str] | None title_blacklist:
            A list of patterns (use `%` to represent zero or more unknown characters and `_`
             to represent a single unknown character)  that should **not** appear in the job's 'title' field.
        :param list[str] | None title_whitelist:
            A list of patterns (use `%` to represent zero or more unknown characters and `_`
            to represent a single unknown character)  that **must** appear in the job's 'title' field.
        """
        #
        if not columns:
            columns = [cls.sql_header_compatible_string(item).lower() for item in cls.default_header]
        new_columns = []
        command_formater = SQLCommandFormater()
        cls._sql_generate_command_select(columns, command_formater)

        command_formater.select_command_conclusion.append(f"{cls.main_table_name}")
        command_formater.group_by_command.append(f"{cls.main_table_name}.url")

        having_condition = ""

        if keywords:
            cls._sql_generate_command_from_list(
                keywords,
                command_formater,
                main_table=cls.main_table_name,
                main_join_on="url",
                second_table=cls.keywords_table_name,
                second_join_on="url",
                column_to_check="keyword",
                column_to_keep="occurrence",
                suffix="_occurence",
                having_condition=having_condition,
                new_columns=new_columns,
            )
            having_condition = "AND"

        if distances_from:
            cls._sql_generate_command_from_list(
                distances_from,
                command_formater,
                main_table=cls.main_table_name,
                main_join_on="localisation",
                second_table=cls.distances_table_name,
                second_join_on="job_localisation",
                column_to_check="reference_localisation",
                column_to_keep="distance",
                relax=distance_relax,
                suffix="_km",
                having_condition=having_condition,
                new_columns=new_columns,
            )
            having_condition = "AND"

        if metadata:
            cls._sql_generate_command_from_list(
                metadata,
                command_formater,
                main_table=cls.main_table_name,
                main_join_on="url",
                second_table=cls.metadata_table_name,
                second_join_on="url",
                column_to_check="key",
                column_to_keep="value",
                suffix="_metadata",
                having_condition=having_condition,
                no_condition_allowed=True,
                new_columns=new_columns
            )
            having_condition = "AND"

        if time_stamp:
            cls._sql_generate_command_from_list(
                time_stamp,
                command_formater,
                main_table=cls.main_table_name,
                main_join_on="url",
                second_table=cls.time_stamps_table_name,
                second_join_on="url",
                column_to_check="keyword",
                column_to_keep="time_stamp",
                suffix="_ts",
                having_condition=having_condition,
                no_condition_allowed=False,
                new_columns=new_columns
            )

        first_condition = cls._sql_generate_command_where(
            cls.main_table_name,
            "contract",
            command_formater,
            contract_whitelist,
            blacklist=False,
            first_condition=True
        )
        first_condition = cls._sql_generate_command_where(
            cls.main_table_name,
            "contract",
            command_formater,
            contract_blacklist,
            blacklist=True,
            first_condition=first_condition
        )

        first_condition = cls._sql_generate_command_where(
            cls.main_table_name,
            "field",
            command_formater,
            field_whitelist,
            blacklist=False,
            first_condition=first_condition
        )
        first_condition = cls._sql_generate_command_where(
            cls.main_table_name,
            "field",
            command_formater,
            field_blacklist,
            blacklist=True,
            first_condition=first_condition
        )

        first_condition = cls._sql_generate_command_where(
            cls.main_table_name,
            "origin",
            command_formater,
            origin_whitelist,
            blacklist=False,
            first_condition=first_condition
        )
        first_condition = cls._sql_generate_command_where(
            cls.main_table_name,
            "origin",
            command_formater,
            origin_blacklist,
            blacklist=True,
            first_condition=first_condition
        )

        first_condition = cls._sql_generate_command_where(
            cls.main_table_name,
            "title",
            command_formater,
            title_whitelist,
            blacklist=False,
            first_condition=first_condition
        )

        first_condition = cls._sql_generate_command_where(
            cls.main_table_name,
            "title",
            command_formater,
            title_blacklist,
            blacklist=True,
            first_condition=first_condition
        )

        if before:
            if first_condition:
                operator = "   "
                first_condition = False
            else:
                operator = "AND"

            command_formater.where_command.append(f"{operator} {cls.main_table_name}.time_stamp <= ?")
            command_formater.where_arguments.append(before)

        if after:
            if first_condition:
                operator = "   "
                first_condition = False
            else:
                operator = "AND"
            command_formater.where_command.append(f"{operator} {cls.main_table_name}.time_stamp >= ?")
            command_formater.where_arguments.append(after)

        if order_by:
            cls._order_by(order_by, columns, new_columns, command_formater)

        command, args = command_formater.construct()

        return command, args

    @classmethod
    def _order_by(cls, order_by, columns, new_columns, sfc):
        valid_column_names = {*columns, *new_columns}

        i = 0
        for columns in order_by:
            if columns not in valid_column_names:
                cls.logger.warning("Unknown column name (for this command) (ORDER BY) : "
                                "'%s' Ignored. For this command, valid columns names are : %s",
                                columns, valid_column_names)
                continue

            sfc.order_by_command.append(columns)
            i += 1

    @classmethod
    def _sql_generate_command_where(
            cls,
            table,
            column,
            scf,
            sql_like_regex_list: list[str] | None = None,
            blacklist=True,
            first_condition=True,
    ):
        if not sql_like_regex_list:
            return first_condition

        if blacklist:
            b_condition = "NOT"
        else:
            b_condition = "   "

        for items in sql_like_regex_list:
            if first_condition:
                condition = "   "
                first_condition = False
            else:
                condition = "AND"
            scf.where_command.append(
                f"{condition} {b_condition} {table}.{column} LIKE ? COLLATE NOCASE"
            )
            scf.where_arguments.append(items)

        return first_condition

    @classmethod
    def sql_run_display_command(cls, command: str, *args, sep="\t", display, file):
        results = cls.sql_run_with_header(command, *args)

        if file:
            flux = open(file, "w", encoding="utf-8")
        else:
            flux = None

        header = (
            "#Command :\n"
            f"{cls._format_sql(command, args)}\n"
            f"\n"
            f"#Line number :\n"
            f"{len(results) - 1} lines\n"
        )

        if cls.log_file:
            header += (
                "\n#Logs :\n"
                f"{cls.log_file.name}\n\n"
            )

        header += (
            f"#{sep.join([header[0] for header in results[0]])}\n"
        )

        if flux:
            flux.write(header)

        if display:
            print(header, end="")

        for job in results[1:]:
            line = sep.join([str(item) for item in job])

            if display:
                print(line)

            if flux:
                flux.write(line)
                flux.write("\n")

        if flux:
            flux.close()



    # --- Main command ---
    # --- --- Requests --- ---
    # --- --- --- --- Sqlite --- --- ---
