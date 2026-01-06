import os

import click
import cloup

from job_scrapper import JobScrapperSkeleton

JOBS = JobScrapperSkeleton.get_table("jobs")
KEYWORDS = JobScrapperSkeleton.get_table("keywords")
METADATA = JobScrapperSkeleton.get_table("metadata")
TIMESTAMP = JobScrapperSkeleton.get_table("timestamps")
DISTANCES = JobScrapperSkeleton.get_table("distances")
JOB_REQUESTER = JobScrapperSkeleton.get_job_requester()


@cloup.command()
@click.option(
    "-c",
    "--columns",
    multiple=True,
    help=(
        "A list of column names. Each selected column will be displayed in the final result. "
        f"By default, all column are displayed. Columns are : {list(JOBS.get_columns_using_sql_name())}. "
        "See `request-format-help` to known how to filter results."
    ),
)
@click.option(
    "-d",
    "--distances-from",
    multiple=True,
    help=(
        "Add columns that contains distances from reference places. "
        f"e.g. `-d Paris, france` -> add a column named 'Paris, France{JobScrapperSkeleton.distance_suffix}' "
        f"that contains the distance from each job to `Paris, France`. "
        "See `request-format-help` to known how to filter results. "
        f"Use `enumerate-column-value {DISTANCES.__tablename__} reference_localisation` to have a list of all column "
        f"available in the current database."
    ),
)
@click.option(
    "-k",
    "--keywords",
    multiple=True,
    help=(
        "Add columns that contains the number of occurrences of a keyword (and said keyword alliases)"
        "contained in a job offer entry."
        f"e.g. `-k Informatics` -> add a column named 'Informatics{JobScrapperSkeleton.keyword_suffix}' that"
        f"contains the number of occurrences of `Informatics` related keywords."
        "See `request-format-help` to known how to filter results. "
        f"Use `enumerate-column-value {KEYWORDS.__tablename__} keyword` to have a list of all column "
        f"available in the current database."
    ),
)
@click.option(
    "-m",
    "--metadata",
    multiple=True,
    help=(
        "Add columns that contains the metadata attached to a certain key."
        f"e.g. `-m education` -> add a column named 'education{JobScrapperSkeleton.metadata_suffix}'. "
        "See `request-format-help` to known how to filter results. "
        f"Use `enumerate-column-value {METADATA.__tablename__} key` to have a list of all column "
        f"available in the current database."
    ),
)
@click.option(
    "-t",
    "--time-stamps",
    multiple=True,
    help=(
        "Add columns that contains a time stamp related to a certain event."
        f"e.g. `-t '{JobScrapperSkeleton.first_sighting_time_stamp_name}'` "
        f"-> add a column named "
        f"{JobScrapperSkeleton.first_sighting_time_stamp_name}{JobScrapperSkeleton.time_stamp_suffix}' that "
        f"contains the date when the offer has been added to the database for the first time."
        "See `request-format-help` to known how to filter results. "
        f"Use `enumerate-column-value {TIMESTAMP.__tablename__} label` to have a list of all column "
        f"available in the current database."
        # f"Keywords : {JobScrapperSkeleton.get_sql_timestamps()}"
    ),
)
@click.option(
    "-o",
    "--order-by",
    multiple=True,
    help="Expect columns declared with -t, -m, -k, -d or -c. Order those column from left to right and"
         "order entries using values contained in those columns.",
)
@click.option(
    "-a",
    "--after",
    multiple=False,
    help="Only shows the entries found for the last time after a certain date."
         f"Equivalent to `-t {JobScrapperSkeleton.init_time_stamp_name}::>=::[Your date]`",
)
@click.option(
    "-b",
    "--before",
    multiple=False,
    help="Only shows the entries found for the last time before a certain date."
         f"Equivalent to `-t {JobScrapperSkeleton.init_time_stamp_name}::<=::[Your date]`",
)
@cloup.option(
    "--db",
    type=click.Choice(
        list(JobScrapperSkeleton.get_available_databases().keys()),
        case_sensitive=True,
    ),
    default="maindb",
    help="Select the targeted database.",
)
@cloup.pass_context
def request(
    ctx,
    columns=None,
    distances_from=None,
    keywords=None,
    metadata=None,
    time_stamps=None,
    order_by=None,
    after=None,
    before=None,
    db=None,
):
    """Request the selected database (`--db`) and display jobs offer that
    match the request. In order to format what you request, you might want to
    run `request_format_help`"""
    if isinstance(time_stamps, list):
        if after:
            time_stamps.append(f"{JobScrapperSkeleton.init_time_stamp_name}::>=::{after}")

        if before:
            time_stamps.append(f"{JobScrapperSkeleton.init_time_stamp_name}::<=::{before}")


    with JobScrapperSkeleton.get_sql_session(database_name=db, workdir=ctx.obj["workdir"]) as session:
        query = JOB_REQUESTER.build_request(
            session=session,
            columns=columns,
            distances_from=distances_from,
            keywords=keywords,
            metadata=metadata,
            time_stamp=time_stamps,
            order_by=order_by,
        )
        result = JOB_REQUESTER.execute_request(session, query)

    i = 0
    for vals in JOB_REQUESTER.result_to_flat_file_generator(result):
        i += 1
        print(vals)

    print(f"{i} result(s)")


@cloup.command()
def request_format_help():
    """How to format columns that you request using `request`"""
    print(JOB_REQUESTER.get_string_format_help())
