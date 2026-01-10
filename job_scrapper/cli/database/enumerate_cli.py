import os

import click
import cloup

from job_scrapper import JobScrapperSkeleton
from .database_cli import database

@database.group()
def enumerate():
    """Set of method to enumerate database content."""


@enumerate.command()
def tables():
    """Displays each table's names in the database"""
    for names in JobScrapperSkeleton.get_all_tables():
        print(names)


@enumerate.command()
@cloup.argument(
    "table",
    type=click.Choice(
        list(JobScrapperSkeleton.get_all_tables()), case_sensitive=True
    ),
)
def columns(table):
    """Displays columns names attached to a table."""
    all_tables = JobScrapperSkeleton.get_all_tables()
    if table not in all_tables:
        print(table, "is unknown. please use one of :", all_tables)
        exit(1)
    selected_table = all_tables[table]

    for col_names in selected_table.get_columns_using_sql_name():
        print(col_names)


@enumerate.command()
@cloup.argument(
    "table_name",
    type=click.Choice(
        list(JobScrapperSkeleton.get_all_tables()), case_sensitive=True
    ),
    help="The name of the targeted column. Use `enumerate-tables` to discover all tables "
    "available",
)
@cloup.argument(
    "column_name",
    type=str,
    help="The name of the targeted column. Use `enumerate-columns [table]` to discover "
    "all columns attached to a table.",
)
@cloup.pass_context
def column_value(ctx, table_name, column_name):
    """Enumerate through each distinct value contained on the selected column
    of the selected table"""
    all_tables = JobScrapperSkeleton.get_all_tables()
    table = all_tables[table_name]

    with JobScrapperSkeleton.get_sql_session(
        database_name=ctx.obj["database"]
    ) as session:
        try:
            query = table.get_column_values(session, column_name)
        except KeyError as k:
            JobScrapperSkeleton.logger.critical(k)
            exit(1)
        result = session.execute(query)

    for items in result.all():
        print(items[0])
