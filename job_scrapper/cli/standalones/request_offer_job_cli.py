import click
import cloup
from job_scrapper.cli.offers.offers_cli import (
    COLUMN_OPT,
    DISTANCE_OPT,
    KEYWORD_OPT,
    METADATA_OPT,
    TIME_STAMP_OPT,
    ORDER_BY_OPT,
    EXIST_SINCE_AFTER_OPT,
    EXIST_SINCE_BEFORE_OPT,
    LASTLY_SEEN_AFTER_OPT,
    LASTLY_SEEN_BEFORE_OPT,
    CONFIGURATION_FILE_OPT,
    EXPORT_CONFIGURATION_OPT,
    make_list_configuration,
    flat_configuration,
    export_configuration_file,
)
from job_scrapper import JobScrapperSkeleton

JOBS = JobScrapperSkeleton.get_table("jobs")
KEYWORDS = JobScrapperSkeleton.get_table("keywords")
METADATA = JobScrapperSkeleton.get_table("metadata")
TIMESTAMP = JobScrapperSkeleton.get_table("timestamps")
DISTANCES = JobScrapperSkeleton.get_table("distances")
JOB_REQUESTER = JobScrapperSkeleton.get_job_requester()


@cloup.command()
@COLUMN_OPT
@DISTANCE_OPT
@KEYWORD_OPT
@METADATA_OPT
@TIME_STAMP_OPT
@ORDER_BY_OPT
@EXIST_SINCE_AFTER_OPT
@EXIST_SINCE_BEFORE_OPT
@LASTLY_SEEN_AFTER_OPT
@LASTLY_SEEN_BEFORE_OPT
@cloup.option(
    "--db",
    type=click.Choice(
        list(JobScrapperSkeleton.get_available_databases().keys()),
        case_sensitive=True,
    ),
    default="maindb",
    help="Select the targeted database.",
)
@cloup.option(
    "--dry-run",
    is_flag=True,
    help="Only test if this request can be done but do not execute it",
)
@CONFIGURATION_FILE_OPT
@EXPORT_CONFIGURATION_OPT
@cloup.pass_context
def request(
    ctx,
    db=None,
    dry_run=False,
    export_configuration=None,

    **configuration_related_fields,


):
    """Request the selected database (`--db`) and display jobs offer that
    match the request. In order to format what you request, you might want to
    run `request_format_help`"""

    config = make_list_configuration(
        **configuration_related_fields,
    )
    with JobScrapperSkeleton.get_sql_session(database_name=db, workdir=ctx.obj["workdir"]) as session:
        query = JOB_REQUESTER.build_request(
            session=session,
            **flat_configuration(**config)
        )

        if query is None:
            # We assume that any error is logged by
            # query
            print("Unable to complete request.")
            exit(1)

        # we can assume that JOB_REQUESTER.build_request
        # went fine. let's export this configuration
        if export_configuration:
            export_configuration_file(config=config, configuration_file=export_configuration)

        if dry_run:
            print("Dry run completed.")
            return

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

