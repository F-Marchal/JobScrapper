import click
import cloup
from job_scrapper import JobScrapperSkeleton
import os
import json

@cloup.group()
@cloup.pass_context
def database(ctx):
    """A small set of command that can be used to interact with the database."""
    JobScrapperSkeleton.set_workdir(ctx.obj["workdir"])
    if not os.path.exists(JobScrapperSkeleton.get_maindb_path()):
        JobScrapperSkeleton.logger.critical(
            "Can not find the database ('%s'). "
            "Please run `job-scrapper scrap [target]` at least once to create it.",
            JobScrapperSkeleton.get_maindb_path()
        )
        exit(1)

@database.command()
def tables_names():
    """Displays each table's names in the database"""
    for names in JobScrapperSkeleton.get_tables():
        print(names)

@database.command()
@cloup.argument(
    "table",
    type=click.Choice(list(JobScrapperSkeleton.get_tables()), case_sensitive=True),
)
def table_columns(table):
    """Displays columns names attached to a table."""
    all_tables = JobScrapperSkeleton.get_tables()
    if table not in all_tables:
        print(table, "is unknown. please use one of :", all_tables)
        exit(1)
    selected_table = all_tables[table]

    for col_names in selected_table.get_columns_using_sql_name():
        print(col_names)

@database.command()
@cloup.argument(
    "table",
    type=click.Choice(list(JobScrapperSkeleton.get_tables()), case_sensitive=True),
)
@cloup.argument(
    "column_name",
    type=str,
)
def describe_column(table, column_name):
    # TODO: Displace in BaseTable
    column_name = JobScrapperSkeleton.column_name_normaliser(column_name)
    all_tables = JobScrapperSkeleton.get_tables()
    if table not in all_tables:
        print(table, "is unknown. please use one of :", all_tables)
        exit(1)
    selected_table = all_tables[table]

    all_cols = selected_table.get_columns_using_sql_name()
    if column_name not in all_cols:
        print(column_name, f"is not a column of '{table}'. please use one of :", all_cols)

    col = all_cols[column_name]

    info = {
        "name": col.name,
        "type": str(col.type),
        "nullable": col.nullable,
        "primary_key": col.primary_key,
        "default": str(col.default.arg) if col.default is not None else None,
        "foreign_keys": [],
        "check_constraints": [],
        "table_constraints": [],
        "indexes": []
    }

    # Foreign keys
    for fk in col.foreign_keys:
        info["foreign_keys"].append({
            "constraint": str(fk.constraint),
            "target": fk.target_fullname
        })

    # Column-level check constraints
    for constr in col.constraints:
        info["check_constraints"].append(str(constr))

    # Table-level constraints involving this column
    for constr in table.constraints:
        if col.name in [c.name for c in constr.columns]:
            info["table_constraints"].append(str(constr))

    # Indexes involving this column
    for idx in table.indexes:
        if col.name in [c.name for c in idx.columns]:
            info["indexes"].append({
                "name": idx.name,
                "columns": [c.name for c in idx.columns]
            })

    print(json.dumps(info, indent=4))

@database.command()
def archive_url():
    pass

@database.command()
def restore_url():
    pass

@database.command()
def archive_during_request():
    pass

@database.command()
def restore_archive_during_request():
    pass

def request_archive():
    pass
'''
@database.command()
@click.option(
    "-c", "--columns",
    multiple=True,
    type=click.Choice(list(JobScrapperSkeleton.get_sql_column_jobs_table()),
                      case_sensitive=True),
    help=(
        "A list of column names. Each selected column will be displayed in the final result. "
        "By default, all column are displayed."
    )
)
@click.option(
    "-d", "--distances-from",
    multiple=True,
    help=(
        "Display distances from reference places. Places can be any place contained in the list "
        "at the end of this text. You can use them to filter results "
        "by formatting Them as follows: [operator][Place][condition] : Operator should be '&', 'A' (AND), '|', 'O' (OR), '^', 'X' (XOR); "
        "The condition can be '<', '>', '=', '!' followed by a float."
        f"Places : {JobScrapperSkeleton.get_sql_reference_places()}"
    )
)
@click.option(
    "-k", "--keywords",
    multiple=True,
    help=(
        "Display keywords occurrence in a job offer. keywords can be any string  contained in the list  "
        "at the end of this text. You can use them to filter results "
        "by formatting Them as follows: [operator][keywords][condition] : Operator should be '&', 'A' (AND), '|', 'O' (OR), '^', 'X' (XOR); "
        "The condition can be '<', '>', '=', '!' followed by a float."
        f"Keywords : {JobScrapperSkeleton.get_sql_keywords()}"
    )
)
@click.option(
    "-m", "--metadata",
    multiple=True,
    help=(
        "Display metadata attached to a job offer. metadata can be any string contained "
        "in the key of cls.metadata_table_name. You can not use them to filter results."
        f"Metadata : {JobScrapperSkeleton.get_sql_metadata()}"
    )
)
@click.option(
    "-t", "--time-stamps",
    multiple=True,
    help=(
        "Display time-stamps linked to import event during job offer parsing. time-stamps can be any string contained "
        "in the list at the end of this text. You can use them to filter results "
        "by formatting Them as follows: [operator][keyword][condition] : Operator should be '&', 'A' (AND), '|', 'O' (OR), '^', 'X' (XOR); "
        "The condition can be '<', '>', '=', '!' followed by a float. Date should be formated as "
        "'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD' "
        f"Keywords : {JobScrapperSkeleton.get_sql_timestamps()}"
    )
)
@click.option(
    "-o", "--order-by",
    multiple=True,
    help=(
        "Order columns and sort results using those columns."
    )
)
@click.option(
    "--distance-relax",
    is_flag=True,
    help="Do jobs with null values pass all distance filter?"
)
@click.option(
    "-ob", "--origin-blacklist",
    multiple=True,
    help=(
        "A list of patterns that should **not** be contained in the job's 'origin' field."
        "(use `%` to represent zero or more unknown characters and `_` "
        "to represent a single unknown character)"
    )
)
@click.option(
    "-ow", "--origin-whitelist",
    multiple=True,
    help=(
        "A list of patterns that **must** be contained in the job's 'origin' field."
        "(use `%` to represent zero or more unknown characters and `_` "
        "to represent a single unknown character)"
    )
)
@click.option(
    "-fb", "--field-blacklist",
    multiple=True,
    help=(
        "A list of patterns that should **not** appear in the job's 'field' field."
        "(use `%` to represent zero or more unknown characters and `_` "
        "to represent a single unknown character)"
    )
)
@click.option(
    "-fw", "--field-whitelist",
    multiple=True,
    help=(
        "A list of patterns that **must** appear in the job's 'field' field."
        "(use `%` to represent zero or more unknown characters and `_` "
        "to represent a single unknown character)"
    )
)
@click.option(
    "-cb", "--contract-blacklist",
    multiple=True,
    help=(
        "A list of patterns that should **not** appear in the job's 'contract' field."
        "(use `%` to represent zero or more unknown characters and `_` "
        "to represent a single unknown character)"
    )
)
@click.option(
    "-cw", "--contract-whitelist",
    multiple=True,
    help=(
        "A list of patterns that **must** appear in the job's 'contract' field."
        "(use `%` to represent zero or more unknown characters and `_` "
        "to represent a single unknown character)"
    )
)
@click.option(
    "-tb", "--title-blacklist",
    multiple=True,
    help=(
        "A list of patterns that should **not** appear in the job's 'title' field."
        "(use `%` to represent zero or more unknown characters and `_` "
        "to represent a single unknown character)"
    )
)
@click.option(
    "-tw", "--title-whitelist",
    multiple=True,
    help=(
        "A list of patterns that **must** appear in the job's 'title' field."
        "(use `%` to represent zero or more unknown characters and `_` "
        "to represent a single unknown character)"
    )
)
@click.option(
    "-a",
    "--after",
    type=click.DateTime(formats=["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]),
    default="0001-01-01 00:00:00",
    show_default=True,
    help="A date format 'YYYY-MM-JJ' or 'YYYY-MM-JJ HH:MM:SS' Ensure that returned values comes from "
    "job that hava a time stamp newer (>=) than this date. Meaning that this job offer has been seen "
    f"on a website after this date.'"
)
@click.option(
    "-b",
    "--before",
    type=click.DateTime(formats=["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]),
    default=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
    show_default=True,
    help="A date format 'YYYY-MM-JJ' or 'YYYY-MM-JJ HH:MM:SS' Ensure that returned values comes from "
    "job that hava a time stamp older (>=) than this date. Meaning that this job offer has been seen "
    f"on a website before this date. Default is now ('{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}')."
)

@click.option(
    "-f",
    "--file",
    type=click.Path(file_okay=True, dir_okay=False, resolve_path=True),
    help="A file to export the result."
)
@click.option(
    "--no-display",
    is_flag=True,
    help="Do not display the result.",
)'''
def request(
    columns=None,
    distances_from=None,
    keywords=None,
    metadata=None,
    time_stamps=None,
    order_by=None,
    distance_relax=None,
    after=None,
    before=None,
    origin_blacklist=None,
    origin_whitelist=None,
    field_blacklist=None,
    field_whitelist=None,
    contract_blacklist=None,
    contract_whitelist=None,
    title_blacklist=None,
    title_whitelist=None,
    file=None,
    no_display=False,
):
    '''command, args = JobScrapperSkeleton.sql_generate_command(
        columns=columns,
        distances_from=distances_from,
        keywords=keywords,
        metadata=metadata,
        time_stamp=time_stamps,
        order_by=order_by,
        distance_relax=distance_relax,
        after=after.utctimetuple(), # time_struct conversion
        before=before.utctimetuple(), # time_struct conversion
        origin_blacklist=origin_blacklist,
        origin_whitelist=origin_whitelist,
        field_blacklist=field_blacklist,
        field_whitelist=field_whitelist,
        contract_blacklist=contract_blacklist,
        contract_whitelist=contract_whitelist,
        title_blacklist=title_blacklist,
        title_whitelist=title_whitelist,
    )
    JobScrapperSkeleton.sql_run_display_command(command, *args, file=file, display=not no_display)'''
