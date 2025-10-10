from dataclasses import dataclass, field
import time

@dataclass
class SQLCommandFormater:
    select_command: list[str] = field(default_factory=list)
    join_command: list[str] = field(default_factory=list)
    where_command: list[str] = field(default_factory=list)
    having_command: list[str] = field(default_factory=list)
    group_by_command: list[str] = field(default_factory=list)
    order_by_command: list[str] = field(default_factory=list)

    select_command_conclusion: list[str] = field(default_factory=list)
    join_command_conclusion: list[str] = field(default_factory=list)
    having_command_conclusion: list[str] = field(default_factory=list)

    select_arguments: list[str | int | None] = field(default_factory=list)
    join_arguments: list[str | int | None] = field(default_factory=list)
    where_arguments: list[str | int | None | time.struct_time] = field(default_factory=list)
    having_arguments: list[str | int | None] = field(default_factory=list)

    @staticmethod
    def _construct(
            command,
            end_command,
            start_keyword="",
            end_keyword="",
            start_join=",\n\t",
            end_join=" "
    ) -> str:
        return (f"{start_keyword}"
                f"{start_join.join(command)}"
                f"\n{end_keyword}"
                f"{end_join.join(end_command)}\n")

    def _construct_select(self, command: str, command_arg: list, select=True, from_=True):
        command += self._construct(
            self.select_command,
            self.select_command_conclusion,
            start_keyword="SELECT\n\t" if select else "",
            end_keyword="FROM\n\t" if from_ and self.select_command_conclusion else "",
        )
        command_arg.extend(self.select_arguments)
        return command

    def _construct_join(self, command: str, command_arg: list):
        command += self._construct(
            self.join_command,
            self.join_command_conclusion,
            start_keyword="",
            end_keyword="",
            start_join="\n\t",
            end_join="",
        )
        command_arg.extend(self.join_arguments)
        return command

    def _construct_where(self, command: str, command_arg: list, where=True):

        command += self._construct(
            self.where_command,
            [],
            start_keyword="WHERE\n\t" if where else "",
            end_keyword="",
            start_join="\n\t",
            end_join="",
        )
        command_arg.extend(self.where_arguments)
        return command

    def _construct_having(self, command: str, command_arg: list, having=True):
        command += self._construct(
            self.having_command,
            self.having_command_conclusion,
            start_keyword="HAVING\n\t" if having else "",
            end_keyword="",
            start_join="\n\t",
        )
        command_arg.extend(self.having_arguments)
        return command

    def _construct_order_by(self, command: str, order_by=True):
        command += self._construct(
            self.order_by_command,
            [],
            start_keyword="ORDER BY\n\t" if order_by else "",
            end_keyword="",
            start_join=",\n\t",
        )
        return command

    def _select_order_clean(self, to_clean: list[str | int | None | float | time.struct_time]):
        return [element for _, interest in sorted(to_clean)
                for element in (interest if isinstance(interest, list) else [interest])]

    def _select_order(self):
        arg_i = 0
        new_select_argument1 = []
        new_select_argument2 = []
        new_select_command1 = []
        new_select_command2 = []

        for command_line in self.select_command:
            nb_of_argument_expected = command_line.count("?")
            associated_args = self.select_arguments[arg_i:arg_i + nb_of_argument_expected]
            column_name_tmp = (
                command_line.strip()
                .replace('"', '')
                .replace("'", "")
                .replace(".", " ")
            )
            column_name = column_name_tmp.split(" ")[-1]

            if column_name in self.order_by_command:
                new_select_argument1.append([self.order_by_command.index(column_name), associated_args])
                new_select_command1.append([self.order_by_command.index(column_name), command_line])

            else:
                new_select_argument2.extend(associated_args)
                new_select_command2.append(command_line)

            arg_i += nb_of_argument_expected

        self.select_command.clear()
        self.select_command.extend(self._select_order_clean(new_select_command1))
        self.select_command.extend(new_select_command2)

        self.select_arguments.clear()
        self.select_arguments.extend([*self._select_order_clean(new_select_argument1)])
        self.select_arguments.extend([*new_select_argument2])

        print("_1", self.select_command)
        print("_2", self.select_arguments)
        print(self._select_order_clean(new_select_argument1))
        print(new_select_argument2)

    def construct(self, select=True, from_=True, where=True, having=True, order_by=True):
        command = ""
        command_arg = []

        if self.order_by_command:
            self._select_order()

        # Select
        command = self._construct_select(
            command,
            command_arg,
            select,
            from_
        )

        if self.join_command:
            # Join
            command = self._construct_join(
                command,
                command_arg,
            )

        if self.where_command:
            command = self._construct_where(
                command,
                command_arg,
                where
            )

        # Group by is mandatory for Having close
        if self.group_by_command:
            command += "GROUP BY " + ",\n\t".join(self.group_by_command) + "\n"

            if self.having_command:
                command = self._construct_having(
                    command,
                    command_arg,
                    having
                )

        if self.order_by_command:
            command = self._construct_order_by(
                command,
                order_by
            )

        return command, command_arg