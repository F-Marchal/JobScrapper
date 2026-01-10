import click
import cloup
from job_scrapper.tools.logger_core import CoreLogger
import time
import os
from job_scrapper.tools.get_unique_path import get_unique_path

@cloup.group()
@cloup.option(
    "-v",
    "--verbosity",
    type=click.Choice(
        list(CoreLogger.logger_levels), case_sensitive=False
    ),
    default="INFO",
    help="Log level in terminal. Does not affect log file.",
)
@click.option(
    "-w",
    "--workdir",
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True),
    default="./Workdir",
    help="A folder in which the program will store configuration files (when not specified) and output files."
    "Default : './Workdir'",
)
@click.option(
    "--no-log-file",
    is_flag=True,
    help="No log file will be created. Logs will still show in terminal",
)
@cloup.pass_context
def cli(ctx, verbosity="INFO", workdir="./Workdir", no_log_file: bool = False):
    """Welcome in JobScrapper !
    You can use this tool to scrap a number of website in order to extract potential job offers.
    See other commands.
    """
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

    # --- Logging file ---
    ctx.obj["log_file"] = None
    if not no_log_file:
        log_dir = os.path.join(workdir, "Logs")
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)

        formatted_time = time.strftime("%Y-%m-%d_%H:%M:%S")
        logg_file = os.path.join(log_dir, f"{formatted_time}")
        complete_log_file = get_unique_path(
            logg_file, "log"
        )

        CoreLogger.start_file_logging(complete_log_file, level="DEBUG")
        ctx.obj["log_file"] = complete_log_file
        # ctx.obj["logger"].logger.info(
        #     "All logs are written in '%s'",
        #     complete_log_file
        # )

    # --- Log---
    CoreLogger.logger.debug("CLI : %s", locals())
