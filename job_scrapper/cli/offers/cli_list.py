import click
import cloup
from job_scrapper import JobScrapperSkeleton
from .offers_cli_tools import request_builder, REQUEST_BUILDER_OPT, ALL_COMMON_FILTER_OPTS, make_configuration, JOB_REQUESTER, DB_OPT



@cloup.command()
@DB_OPT
@REQUEST_BUILDER_OPT
@ALL_COMMON_FILTER_OPTS
@cloup.pass_context
def request(
    ctx,
    db=None,

    **kwargs
):
    """Request the selected database (`--db`) and display jobs offer that
    match the request. In order to format what you request, you might want to
    run `request_format_help`"""
    make_configuration(ctx, **kwargs)


    with JobScrapperSkeleton.get_sql_session(database_name=db, workdir=ctx.obj["workdir"]) as session:
        query = request_builder(ctx, session, **kwargs)
        result = JOB_REQUESTER.execute_request(session, query)

    i = 0
    for vals in JOB_REQUESTER.result_to_flat_file_generator(result):
        i += 1
        print(vals)

    print(f"{i} result(s)")

