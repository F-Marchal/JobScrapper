import click
import cloup
from job_scrapper.cli.offers_cli import (
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
    make_list_configuration,
    flat_configuration,
)
from job_scrapper import JobScrapperSkeleton

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
@CONFIGURATION_FILE_OPT
@cloup.pass_context
def archive(
    ctx,

    # JOB_REQUESTER
    columns=None,
    distances_from=None,
    keywords=None,
    metadata=None,
    time_stamps=None,
    order_by=None,
    exist_since_after=None,
    exist_since_before=None,
    lastly_seen_after=None,
    lastly_seen_before=None,



    #
    export_configuration=False,
    configuration_file=None,
):
    config = make_list_configuration(
        configuration_file=configuration_file,

        columns=columns,
        distances_from=distances_from,
        keywords=keywords,
        metadata=metadata,
        time_stamps=time_stamps,
        order_by=order_by,
        exist_since_after=exist_since_after,
        exist_since_before=exist_since_before,
        lastly_seen_after=lastly_seen_after,
        lastly_seen_before=lastly_seen_before,
    )
    JobScrapperSkeleton.logger.debug(
        config
    )



