
import cloup
from sqlalchemy.orm import Query

from job_scrapper import JobScrapperSkeleton
from job_scrapper.sql.wrappers.wrapper_comparison import to_datetime_ymd_or_ymd_hms
import json

JOBS = JobScrapperSkeleton.get_table("jobs")
KEYWORDS = JobScrapperSkeleton.get_table("keywords")
METADATA = JobScrapperSkeleton.get_table("metadata")
TIMESTAMP = JobScrapperSkeleton.get_table("timestamps")
DISTANCES = JobScrapperSkeleton.get_table("distances")
JOB_REQUESTER = JobScrapperSkeleton.get_job_requester()

URL_OPT = cloup.option(
    "-u", "--url",
    help='An url to archive. Equivalent to `-c "url::==::[YOUR URL]"`',
    multiple = True,
)
COLUMN_OPT = cloup.option(
    "-c",
    "--columns",
    multiple=True,
    help=(
        "A list of column names. Each selected column will be displayed in the final result. "
        f"By default, all column are displayed. Columns are : {list(JOBS.get_columns_using_sql_name())}. "
        "See `request-format-help` to known how to filter results."
    ),
)
DISTANCE_OPT = cloup.option(
    "-d",
    "--distances-from",
    multiple=True,
    help=(
        "Add columns that contains distances from reference places. "
        f"e.g. `-d Paris, france` -> add a column named 'Paris, France{JobScrapperSkeleton.distance_suffix}' "
        f"that contains the distance from each job to `Paris, France`. "
        "See `request-format-help` to known how to filter results. "
        f"Distances are computed at runtime."
    ),
)
KEYWORD_OPT = cloup.option(
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
METADATA_OPT = cloup.option(
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
TIME_STAMP_OPT = cloup.option(
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
ORDER_BY_OPT = cloup.option(
    "-o",
    "--order-by",
    multiple=True,
    help="Expect columns declared with -t, -m, -k, -d or -c. Order those column from left to right and"
         "order entries using values contained in those columns.",
)
EXIST_SINCE_AFTER_OPT = cloup.option(
    "--exist-since-after",
    multiple=False,
    callback=lambda ctx, param, value: format_date_for_request(
        ctx, param, value,
        ts=JobScrapperSkeleton.first_sighting_time_stamp_name,
        op=">="
    ),
    help="Only shows the entries found for the first time after a certain date."
         f"Equivalent to `-t {JobScrapperSkeleton.first_sighting_time_stamp_name}::>=::[Your date]`",
)
EXIST_SINCE_BEFORE_OPT = cloup.option(
    "--exist-since-before",
    multiple=False,
    callback=lambda ctx, param, value: format_date_for_request(
        ctx, param, value,
        ts=JobScrapperSkeleton.first_sighting_time_stamp_name,
        op="<="
    ),
    help="Only shows the entries found for the first time before a certain date."
         f"Equivalent to `-t {JobScrapperSkeleton.first_sighting_time_stamp_name}::<=::[Your date]`",
)
LASTLY_SEEN_AFTER_OPT = cloup.option(
    "--lastly-seen-after",
    multiple=False,
    callback=lambda ctx, param, value: format_date_for_request(
        ctx, param, value,
        ts=JobScrapperSkeleton.init_time_stamp_name,
        op=">="
    ),
    help="Only shows the entries found for the last time after a certain date."
         f"Equivalent to `-t {JobScrapperSkeleton.init_time_stamp_name}::>=::[Your date]`",
)
LASTLY_SEEN_BEFORE_OPT = cloup.option(
    "--lastly-seen-before",
    multiple=False,
    help="Only shows the entries found for the last time before a certain date."
         f"Equivalent to `-t {JobScrapperSkeleton.init_time_stamp_name}::<=::[Your date]`",
    callback=lambda ctx, param, value: format_date_for_request(
        ctx, param, value,
        ts=JobScrapperSkeleton.init_time_stamp_name,
        op="<="
    ),
)

CONFIGURATION_FILE_OPT = cloup.option(
    "--configuration-file",
    type=cloup.Path(
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    help="Load configuration from a file.",
)
EXPORT_CONFIGURATION_OPT = cloup.option(
    "--export-configuration",
    type=cloup.Path(
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    help="Export configuration inside a file.",
)

DRY_RUN_OPT = cloup.option(
    "--dry-run",
    is_flag=True,
    help="Only test if this request can be done but do not execute it",
)


REQUEST_BUILDER_OPT = cloup.option_group(
    "Configuration management options",
    DRY_RUN_OPT,
    EXPORT_CONFIGURATION_OPT,
)
ALL_COMMON_FILTER_OPTS = cloup.option_group(
    "Filtering options",
    COLUMN_OPT,
    URL_OPT,
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
)


def format_date_for_request(
        ctx,
        param,
        value,
        ts: str,
        op: str,
):
    if value is None:
        return None
    to_datetime_ymd_or_ymd_hms(
        value,
    ) # raise error when invalid value

    return f"{ts}::{op}::{value}"

def make_list_configuration(
        configuration_file: str | None = None,
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
        **_
) -> dict:
    if configuration_file:
        try:
            with open(configuration_file, "r") as f:
                config = json.load(
                    f,
                )
        except Exception as e:
            JobScrapperSkeleton.logger.error(
                "Unable to load configuration file ('%s').\n%s",
                configuration_file,
                e
            )
            raise
    else:
        config = {}


    new_values = {
        "columns": columns,
        "distances_from": distances_from,
        "keywords": keywords,
        "time_stamps": time_stamps,
        "metadata": metadata,
        "order_by": order_by,
        "exist_since_after": exist_since_after,
        "exist_since_before": exist_since_before,
        "lastly_seen_after": lastly_seen_after,
        "lastly_seen_before": lastly_seen_before,
    }

    for k, value in new_values.items():
        if not value:
            continue

        if k not in config or not config[k]:
            config[k] = value
            continue

        if isinstance(config[k], list) and isinstance(value, (list, tuple, set)):
            config[k] = list(set(config[k]).union(value))

    JobScrapperSkeleton.logger.debug("Configuration : %s", config)
    return config

def flat_configuration(
        time_stamps = None,
        exist_since_after = None,
        exist_since_before = None,
        lastly_seen_after = None,
        lastly_seen_before = None,
        **kwargs
):
    kwargs["time_stamps"] = merge_timestamps(
        time_stamps=time_stamps,
        exist_since_after=exist_since_after,
        exist_since_before=exist_since_before,
        lastly_seen_after=lastly_seen_after,
        lastly_seen_before=lastly_seen_before,
    )
    return kwargs


def make_configuration(
        ctx,

        urls: tuple[str] | list[str] | None = None,
        configuration_file: str | None = None,

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

        **_
):
    if urls:
        if not columns:
            columns = []
        columns = [
            *[f"|::url::==::{url}"  for url in urls],
            *columns]

    raw_config = make_list_configuration(
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

    ctx.obj["raw_configuration"] = raw_config
    ctx.obj["configuration"] = flat_configuration(**raw_config)
    return ctx.obj["configuration"]


def export_configuration_file(config: dict, configuration_file: str):
    try:
        with open(configuration_file, "w") as f:
            json.dump(
                config,
                f,
                indent=2,
                ensure_ascii=False,
            )
    except Exception as e:
        JobScrapperSkeleton.logger.error(
            "Unable to export configuration file ('%s').\n%s",
            configuration_file,
            e
        )
        raise


def merge_timestamps(
        time_stamps=None,
        exist_since_after=None,
        exist_since_before=None,
        lastly_seen_after=None,
        lastly_seen_before=None,
) -> list[str] | None:
    if time_stamps is None:
        time_stamps = []
    else:
        time_stamps = list(time_stamps)

    if exist_since_after is not None:
         time_stamps.append(exist_since_after)

    if exist_since_before is not None:
        time_stamps.append(exist_since_before)

    if lastly_seen_after is not None:
        time_stamps.append(lastly_seen_after)

    if lastly_seen_before is not None:
        time_stamps.append(lastly_seen_before)

    return time_stamps if time_stamps else None


def request_builder(ctx, session, export_configuration: str | None = None, dry_run: bool=False, **_) -> Query | None:
    config = ctx.obj["configuration"]
    query = JOB_REQUESTER.build_request(
        session=session,
        **config
    )

    if not query:
        raise TypeError("Unable to build request.")

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
        return None

    return query


