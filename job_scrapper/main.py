import logging
import os.path
from gc import callbacks

import click
import cloup
import time
from datetime import datetime

from job_scrapper import (
    JobScrapperSkeleton,
    CHUMtpScrapper,
    CiradScrapper,
    CNRScrapper,
    INRAEScrapper,
    InsermScrapper,
    IRDScrapper,
    SanofiScrapper,
    SBIScrapper,
)


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
    JobScrapperSkeleton.workdir = workdir

    # --- Logging file ---
    if not no_log_file:
        log_dir = os.path.join(workdir, "Logs")
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)

        local_time = time.localtime()
        formatted_time = time.strftime("%Y-%m-%d_%H:%M:%S")
        logg_file = os.path.join(log_dir, f"{formatted_time}")
        complete_log_file = JobScrapperSkeleton.get_unique_file_name(logg_file, "log")

        JobScrapperSkeleton.start_file_logging(complete_log_file, level="DEBUG")

    # --- Log---
    JobScrapperSkeleton.logger.debug("CLI : %s", locals())

# --- --- --- Database --- --- ---
def _parse_date_or_datetime(_, __, value):
    if value is None:
        return None

    formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    raise click.BadParameter(
        f"Invalid date format: {value}. Expected 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'."
    )

def _execute_sql_command(command: str, format_list: None | list = None) -> str:
    if format_list is None:
        format_list = []

    JobScrapperSkeleton.logger.debug("Executing sql command : %s\nFormat list : %s", command, format_list)

    with JobScrapperSkeleton.write_in_database() as cursor:
        cursor.execute(command, format_list)
        result = cursor.fetchall()

    logging.debug("Result : %", result)
    return result


@cli.group()
@cloup.pass_context
@click.option(
    "-a",
    "--after",
    callback=_parse_date_or_datetime,
    default=None,
    help="A date format 'YYYY-MM-JJ' or 'YYYY-MM-JJ HH:MM:SS' When applicable, ensure that returned values comes from "
         "job that hava a time stamp older (>=) than this date. This mean that this job offer has been seen "
         "on a website after this date",
)

def database(ctx, after):
    """A small set of command that can be used to interact with the database."""
    if after:
        ctx.obj["after"] = after
    else:
        ctx.obj["after"] = datetime.min

@database.command()
@cloup.argument(
    'command',
    help="An sqlite command that will be executed on scrapper's database."
)
def execute(command):
    """Execute sqlite code."""
    for line in _execute_sql_command(
        command
    ):
        print(line)


@database.command()
@cloup.argument(
    'job-url',
    help="Job's url"
)
def get_job_page(job_url):
    """If it exists, will return a path that lead to a .zip / .pdf that contain the offer."""
    print("#url")
    for line in _execute_sql_command(
        f"""
        SELECT * FROM Metadata 
        where url="{job_url}"
        and key="job_page";
        """
    ):
        print(os.path.abspath(line[2]))


@database.command()
@cloup.pass_context
@cloup.argument(
    'localisation',
    help="A localisation (e.g. 'Paris, France')"
)
@click.option(
    "-m",
    "--max-distance",
    type=float,
    default=100,
    help="Jobs returned by this command can not be further away than this value (km). default : 100",
)
def get_job_near(ctx, localisation, max_distance):
    """Displays all job near enough a localisation. /!\\ Some jobs have missing / non-standard location
     and thus will be excluded from this command ! """
    print(f"#Job_localisation\tdistance_to_{localisation}\tlast_sighting\turl")
    for line in _execute_sql_command(
        f"""
        SELECT localisation, distances.distances, time_stamp, url
        FROM Jobs
        JOIN distances
          ON (Jobs.localisation = distances.localisation1  OR Jobs.localisation = distances.localisation2)
          WHERE (distances.localisation1 == "{localisation}" or distances.localisation2 == "{localisation}")
          AND time_stamp >= '{ctx.obj["after"]}'
          AND distances.distances <= {max_distance}
          ORDER BY distances.distances ASC, time_stamp DESC;
        """
    ):
        print("\t".join([str(c) for c in line]))

@database.command()
def known_localisation():
    """Displays a list of all localisations that can be used into get_job_near"""
    print(f"#Places")
    for line in _execute_sql_command(
        """
        SELECT DISTINCT place
        FROM (
            SELECT localisation1 AS place
            FROM distances
            UNION
            SELECT localisation2 AS place
            FROM distances
        );
        """
    ):
        print("\t".join(line))

# --- --- ---Database --- --- ---
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
    'By default "Workdir/known-urls.json" is used.',
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
    "--no-sql-export (-q) is used, this flag"
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
    """Scraps Montpellier CHU's job offer. """
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
    SBIScrapper.main(**ctx.obj["OptionsScrapperMain"])
# --- --- --- SCRAP group --- --- ---

def main():
    cli()

if __name__ == "__main__":
    cli()
