import os
import time
from importlib.metadata import version  # , PackageNotFoundError

import click
import cloup

from job_scrapper import JobScrapperSkeleton
from job_scrapper.tools.get_unique_path import get_unique_path
from job_scrapper.tools.logger_core import CoreLogger

TOOL_NAME = "job-scrapper"
__version__ = version(TOOL_NAME)


@cloup.group(
    help=f"""Welcome in `{TOOL_NAME}` {__version__} !
    You can use this tool to scrap a number of website in order to extract potential job offers.
    If you just installed it, you might want to run `{TOOL_NAME} configure keywords` in order to select
    which keywords you want to search in offers. To start retrieving offer from websites,
    check `{TOOL_NAME} fetch-offers`. At last, to consult offer you retrieved, check `{TOOL_NAME} offers`.
    """
)
@cloup.option(
    "-v",
    "--verbosity",
    type=click.Choice(list(CoreLogger.logger_levels), case_sensitive=False),
    default="INFO",
    help="Log level in terminal. Does not affect log file.",
    show_default=True,
)
@cloup.version_option(__version__)
@click.option(
    "-w",
    "--workdir",
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True),
    show_default=True,
    default="./Workdir",
    help="A folder in which the program will store job database, downloaded offers, logs and other files.",
)
@click.option(
    "--no-log-file",
    is_flag=True,
    help="No log file will be created. Logs will still show in terminal",
)
@cloup.pass_context
def cli(
    ctx,
    verbosity="INFO",
    workdir="./Workdir",
    no_log_file: bool = False,
    show_version: bool = False,
):
    """
    :param ctx: cli context object
    :param verbosity: Verbosity level see CoreLogger.logger_levels
    :param workdir: Where the program will store / read configuration / result / logs files (when not specified)
    :param no_log_file: Disable logging copy in file.
    :param show_version: Show version and exit
    :return:
    """
    if show_version:
        print(version)
        return

    if ctx.obj is None:
        ctx.obj = {}

    ctx.obj["logger"] = CoreLogger

    # --- Verbose ---
    ctx.obj["logger"].set_logging_level(verbosity)
    ctx.obj["verbosity"] = verbosity

    # --- Workdir ---
    if not os.path.exists(workdir):
        os.mkdir(workdir)

    ctx.obj["workdir"] = workdir
    JobScrapperSkeleton.set_workdir(workdir)

    # --- Logging file ---
    ctx.obj["log_file"] = None
    if not no_log_file:
        log_dir = os.path.join(workdir, "Logs")
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)

        formatted_time = time.strftime("%Y-%m-%d_%H:%M:%S")
        logg_file = os.path.join(log_dir, f"{formatted_time}")
        complete_log_file = get_unique_path(logg_file, "log")

        CoreLogger.start_file_logging(complete_log_file, level="DEBUG")
        ctx.obj["log_file"] = complete_log_file
        # ctx.obj["logger"].logger.info(
        #     "All logs are written in '%s'",
        #     complete_log_file
        # )

    # --- Log---
    CoreLogger.logger.debug("CLI : %s", locals())
