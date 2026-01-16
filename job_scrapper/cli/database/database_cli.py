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



@cloup.group()
@cloup.pass_context
@cloup.option(
    "--db",
    type=click.Choice(
        list(JobScrapperSkeleton.get_available_databases().keys()),
        case_sensitive=True,
    ),
    default="maindb",
    help="Select the targeted database.",
)
def database(ctx, db):
    """A small set of command that can be used to interact with the database."""
    JobScrapperSkeleton.set_workdir(ctx.obj["workdir"])
    ctx.obj["database"] = db
    if not os.path.exists(JobScrapperSkeleton.get_database_path()):
        JobScrapperSkeleton.logger.critical(
            "Can not find the database ('%s'). "
            "Please run `job-scrapper scrap [target]` at least once to create it.",
            JobScrapperSkeleton.get_maindb_path(),
        )
        exit(1)

