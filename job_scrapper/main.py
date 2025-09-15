import click
import cloup

from job_scrapper import CiradScrapper, JobScrapperSkeleton


@cloup.group()
@cloup.option(
    "-v",
    "--verbosity",
    type=click.Choice(
        list(JobScrapperSkeleton.logger_levels), case_sensitive=False
    ),
    default="INFO",
    help="Niveau de logs",
)
@cloup.pass_context
def cli(ctx, verbosity="INFO"):
    """Main Command line Interface. Will be specialised later on."""
    JobScrapperSkeleton.set_logging_level(verbosity)
    ctx.obj = {"verbosity": verbosity}


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
    "-w",
    "--workdir",
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True),
    default="./Workdir",
    help="A folder in which the program will store configuration files (when not specified) and output files."
    "Default : './Workdir'",
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
    help="Write the result of the scrapping inside a file. /!\\ This file will be overwritten.",
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
    workdir,
    no_coordinates_update,
    no_urls_update,
    save_job_page,
    display,
    result_file,
    no_sql_export,
):
    """Scrap a specific website (see command section) to extract job offers. By default,
    the results are exported inside a sqlite database.
    General information can be retrieved from all website such as job name, job localisation, job field, and more.
    More specific information like job distance to a certain place (--ref-places) or the number of occurrences of
    certain keyword can also be obtains (--keywords)."""
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
    ctx.obj["workdir"] = workdir
    JobScrapperSkeleton.workdir = workdir


@scrap.command()
@cloup.pass_context
def sanofi(ctx):
    """Scrap sanofi website for job offers."""


@scrap.command()
@cloup.pass_context
def cirad(ctx):
    """Scrap en mode B (complet)."""
    CiradScrapper.main(**ctx.obj["OptionsScrapperMain"])


if __name__ == "__main__":
    cli()
