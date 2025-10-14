import os.path
import time

import click
import cloup
from click import pass_context

from job_scrapper import (
    CHUMtpScrapper,
    CiradScrapper,
    CNRScrapper,
    FranceGenomiqueScrapper,
    IfremerScrapper,
    INRAEScrapper,
    InsermScrapper,
    IRDScrapper,
    JobScrapperSkeleton,
    SanofiScrapper,
    SFBIScrapper,
)

JobScrapperSkeleton.set_logging_level("CRITICAL")

@cloup.group()
@cloup.option(
    "-v",
    "--verbosity",
    type=click.Choice(
        list(JobScrapperSkeleton.logger_levels), case_sensitive=False
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
    # --- Verbose ---
    JobScrapperSkeleton.set_logging_level(verbosity)
    ctx.obj = {"verbosity": verbosity}

    # --- Workdir ---
    if not os.path.exists(workdir):
        os.mkdir(workdir)

    ctx.obj["workdir"] = workdir
    JobScrapperSkeleton.set_workdir(workdir)

    # --- Logging file ---
    if not no_log_file:
        log_dir = os.path.join(workdir, "Logs")
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)

        formatted_time = time.strftime("%Y-%m-%d_%H:%M:%S")
        logg_file = os.path.join(log_dir, f"{formatted_time}")
        complete_log_file = JobScrapperSkeleton.get_unique_path(
            logg_file, "log"
        )

        JobScrapperSkeleton.start_file_logging(complete_log_file, level="DEBUG")

    # --- Log---
    JobScrapperSkeleton.logger.debug("CLI : %s", locals())

'''
# --- --- --- Database --- --- ---
@cli.group()
def database():
    """A small set of command that can be used to interact with the database."""
    if not os.path.exists(JobScrapperSkeleton.get_maindb_path()):
        JobScrapperSkeleton.logger.critical(
            "Can not find the database ('%s'). "
            "Please run `job-scrapper scrap [target]` at least once to create it.",
            JobScrapperSkeleton.get_maindb_path()
        )
        exit(1)

@database.command()
def job_columns():
    """Display each column of the 'job' table."""
    for col in JobScrapperSkeleton.get_sql_column_jobs_table():
        print(col)

@database.command()
def tables_names():
    """Displays each table's names in the database"""
    for names in JobScrapperSkeleton.get_sql_table_names():
        print(names)

@database.command()
@click.argument(
    "table",
    type=click.Choice(list(JobScrapperSkeleton.get_sql_table_names()), case_sensitive=True),
)
def table_columns(table):
    """Displays columns names attached to a table."""
    for vals in JobScrapperSkeleton.get_sql_table_column_name(table):
        print(vals)

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
)
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
    command, args = JobScrapperSkeleton.sql_generate_command(
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
    JobScrapperSkeleton.sql_run_display_command(command, *args, file=file, display=not no_display)
'''

# --- --- --- SCRAP group --- --- ---
@cli.group()
@cloup.pass_context
@click.option(
    "-r",
    "--ref-places",
    type=click.File("r"),
    default=None,
    help="A JSON file containing a list of places. The program will compute the distances (km) that separate"
    'a job offer from those places. E.g. ["Paris, France", "London, UK", "Sheffield, UK"]'
    "By default Workdir/researched-localisation",
)
@click.option(
    "-k",
    "--keywords",
    type=click.File("r"),
    default=None,
    help="A JSON file containing a number of keywords. The program will seek and count those keywords inside each job offer."
    'The JSON file should look like : {"keywords": ["keyword", "alias1", "alias2"...]} '
    'E.g {"Artificial intelligence": ["Artificial intelligence", "IA", "LLM", "Neural Networks"]} In this example,'
    ' each occurrences of "Artificial intelligence", "IA", "LLM", "Neural Networks" will increment the counter'
    'By default "Workdir/researched-keywords.json"',
)
@click.option(
    "-c",
    "--coordinates",
    type=click.File("r"),
    default=None,
    help="A JSON file containing a number of places associated with there coordinate (latitude, longitude). "
    "This will speed up the the program when it compute the distances (km) that separate a job offer from a place. "
    "At the end of the program, this file will be updated with newly encountered localisation. Use "
    "`--no-coordinates-update` to disable this behaviour\n"
    'The JSON file should look like : {"places": [latitude, longitude]}. '
    'E.g  {"Paris, France": [48.8534951, 2.3483915]}.\n'
    'By default "Workdir/known-localisation.json" is used',
)
@click.option(
    "-i",
    "--ignore-urls",
    type=click.File("r"),
    default=None,
    help="A JSON file containing a number of urls. When the job offer's url is contained inside it, the following "
    "processing will not occurred : 1. keywords researched 2. distances computation 3. html download."
    "At the end of the program, this file will be updated with newly encountered url. Use "
    "`--no-urls-update` to disable this behaviour."
    'The JSON file should look like :  ["urls"].'
    'By default "Workdir/.known-urls.json" is used.',
)
@click.option(
    "--no-coordinates-update",
    is_flag=True,
    help="Turn this flag on to disable coordinates's json updates",
)
@click.option(
    "--no-urls-update",
    is_flag=True,
    help="Turn this flag on to disable ignore-urls's json updates ",
)
@click.option(
    "-s",
    "--save-job-page",
    is_flag=True,
    help="Job's web pages will be download and stored inside the workdir.",
)
@click.option(
    "-d",
    "--display",
    is_flag=True,
    help="Output the result inside the terminal. If --result-file (-f) is not used and "
    "--no-sql_core-export (-q) is used, this flag"
    "is turned on by default.",
)
@click.option(
    "-f",
    "--result-file",
    type=click.Path(file_okay=True, dir_okay=False, resolve_path=True),
    default=None,
    help="Write the result of the scrapping inside a file. /!\\ If this file exist, this file will be overwritten.",
)
@click.option(
    "-q",
    "--no-sql-export",
    is_flag=True,
    help="The result will not be exported inside a database in the workdir.",
)
# pylint: disable=R0913
# pylint: disable=R0917
# having many arguments is expected for this command
def scrap(
    ctx,
    ref_places,
    keywords,
    coordinates,
    ignore_urls,
    no_coordinates_update,
    no_urls_update,
    save_job_page,
    display,
    result_file,
    no_sql_export,
):
    """Scraps a specific website (see command section) to extract job offers. By default,
    the results are exported inside a sqlite database.
    General information can be retrieved from all website such as job name, job localisation, job field, and more.
    More specific information like job distance to a certain place (--ref-places) or the number of occurrences of
    certain keyword can also be obtains (--keywords)."""
    JobScrapperSkeleton.logger.debug("Scrap : %s", locals())
    ctx.obj["OptionsScrapperMain"] = {
        "localisations_to_search_json": ref_places,
        "keywords_to_search_json": keywords,
        "known_localisations_json": coordinates,
        "known_urls_json": ignore_urls,
        "dump_localisations": not no_coordinates_update,
        "dumb_urls": not no_urls_update,
        "save_job_page": save_job_page,
        "display": display or (no_sql_export and not result_file),
        "flat_export": result_file,
    }


@scrap.command()
@cloup.pass_context
def chu_mpt(ctx):
    """Scraps Montpellier CHU's job offer."""
    CHUMtpScrapper.main(**ctx.obj["OptionsScrapperMain"])


@scrap.command()
@cloup.pass_context
def cirad(ctx):
    """Scraps Cirad's website. ('Centre de coopération internationale en recherche agronomique pour le développement')"""
    CiradScrapper.main(**ctx.obj["OptionsScrapperMain"])


@scrap.command()
@cloup.pass_context
def cnrs(ctx):
    """Scrap CNRS job offers 'Centre national de la recherche scientifique'"""
    CNRScrapper.main(**ctx.obj["OptionsScrapperMain"])


@scrap.command()
@cloup.pass_context
def france_genomique(ctx):
    """Scraps jobs from France Genomics's website. Not tested with many offers !!"""
    FranceGenomiqueScrapper.main(**ctx.obj["OptionsScrapperMain"])


@scrap.command()
@cloup.pass_context
def ifremer(ctx):
    """Scrapss jobs from ifremer. 'French research institute for the exploitation of maritime environment'"""
    IfremerScrapper.main(**ctx.obj["OptionsScrapperMain"])


@scrap.command()
@cloup.pass_context
def inrae(ctx):
    """Scrapss jobs from INRAE's website. 'Institut national de recherche pour l’agriculture,
    l’alimentation et l’environnement'"""
    INRAEScrapper.main(**ctx.obj["OptionsScrapperMain"])


@scrap.command()
@cloup.pass_context
def inserm(ctx):
    """Scraps 'CDD Ingénieurs et Techniciens' jobs from INSERM's ('Institut national de
    la santé et de la recherche médicale') website. 'Mobilité Chercheurs', 'CDD Chercheurs'
    and 'Mobilité Ingénieurs et Techniciens' are ignored."""
    InsermScrapper.main(**ctx.obj["OptionsScrapperMain"])


@scrap.command()
@cloup.pass_context
def ird(ctx):
    """Scraps jobs from IRD's website. ('Institut de recherche pour le développement')"""
    IRDScrapper.main(**ctx.obj["OptionsScrapperMain"])


@scrap.command()
@cloup.pass_context
def sanofi(ctx):
    """Scraps Sanofi's website (Job offers are limited to 'France')."""
    SanofiScrapper.main(**ctx.obj["OptionsScrapperMain"])


@scrap.command()
@cloup.pass_context
def sfbi(ctx):
    """Scraps SFBI's website. ('Société Française de Bioinformatique')"""
    SFBIScrapper.main(**ctx.obj["OptionsScrapperMain"])


# --- --- --- SCRAP group --- --- ---


def main():
    """Start JobScrapper's Command Line Interface"""
    cli()


if __name__ == "__main__":
    cli()
