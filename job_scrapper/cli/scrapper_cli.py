from cli.cli_base import click, cloup

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

@cloup.group()
@cloup.option(
    "-r",
    "--ref-places",
    type=click.File("r"),
    default=None,
    help="A JSON file containing a list of places. The program will compute the distances (km) that separate"
    'a job offer from those places. E.g. ["Paris, France", "London, UK", "Sheffield, UK"]'
    "By default Workdir/researched-localisation",
)
@cloup.option(
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
@cloup.option(
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
@cloup.option(
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
@cloup.option(
    "--no-coordinates-update",
    is_flag=True,
    help="Turn this flag on to disable coordinates's json updates",
)
@cloup.option(
    "--no-urls-update",
    is_flag=True,
    help="Turn this flag on to disable ignore-urls's json updates ",
)
@cloup.option(
    "-s",
    "--save-job-page",
    is_flag=True,
    help="Job's web pages will be download and stored inside the workdir.",
)
@cloup.option(
    "-d",
    "--display",
    is_flag=True,
    help="Output the result inside the terminal. If --result-file (-f) is not used and "
    "--no-sql-export (-q) is used, this flag"
    "is turned on by default.",
)
@cloup.option(
    "-f",
    "--result-file",
    type=click.Path(file_okay=True, dir_okay=False, resolve_path=True),
    default=None,
    help="Write the result of the scrapping inside a file. /!\\ If this file exist, this file will be overwritten.",
)
@cloup.option(
    "-q",
    "--no-sql-export",
    is_flag=True,
    help="The result will not be exported inside a database in the workdir.",
)
@cloup.pass_context
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
    """Scraps jobs from INSERM's ('Institut national de
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
