import click
import cloup
from job_scrapper.cli.configure.cli_contact import CONTACT_OPTION, ask_contact
from job_scrapper import SCRAPER_REGISTRY, JobScrapperSkeleton

@cloup.command()
@cloup.pass_context
@cloup.argument(
    "scrappers",
    required=True,
    type=click.Choice(
        list(sorted(SCRAPER_REGISTRY.keys()))
    ),
    help="Select which website you want to scrap.",
    nargs=-1
)

@CONTACT_OPTION
@cloup.option(
    "-r",
    "--reinspect_offer_after",
    type=int,
    default=14,
    help="Number of days to wait before reopening the web page containing an offer. "
        "This prevents repeatedly accessing the same offer too frequently.",
    show_default=True,
)
@cloup.option(
    "-t",
    "--tsv",
    is_flag=True,
    help="Also export offers inside TSV files. Those files will be located inside "
         "`[Workdir]/[Scrapper Name]/TSVs/`",
)

@cloup.option(
    "-b",
    "--batch-export",
    type=int,
    default=20,
    help="Group offer exportation to TSV / the database to limit how many time tsv file / database are opened."
         "Use `-b 0` to disable batch exportation.",
    show_default=True,
)
@cloup.option(
    "-f",
    "--retry-webpage-fetch",
    type=int,
    default=2,
    help="How many time the scrapper can retry to fetch an url.",
    show_default=True,
)
@cloup.option(
    "-q",
    "--sleep-before-retry",
    type=float,
    default=2,
    help="How long (in seconds) the scrapper should wait before retrying to fetch an url. (Minimum=0.25 seconds)",
    show_default=True,
)
@cloup.option(
    "-d",
    "--download",
    type=click.Choice([s.value for s in JobScrapperSkeleton.SaveTypes]),
    default=JobScrapperSkeleton.SaveTypes.MHTML,
    help="Will trigger offer download. Offers will be downloads in [Workdir]/[Scrapper Name]/. "
         "Text : Only store text extracted from the offer ; HTML : Store full HTML page or the file that contains the "
         "offer (.pdf...) ; MHTML : Full page storage with images and more. You might need Google Chrome to "
         "open this format of file.",
    show_default=True,
)
@cloup.option(
    "--compress-download",
    is_flag=True,
    help="Should downloaded file (-d) be compressed into a zip archive ?",
)
def scrap(
        ctx,
        scrappers: list[str],
        tsv: bool,
        batch_export: int,
        sleep_before_retry: float,
        reinspect_offer_after: int,
        retry_webpage_fetch: int,
        compress_download: bool,
        contact: str = "",
        download: JobScrapperSkeleton.SaveTypes | None = None,
):
    """
    Extract job offer from one (or more) website. Extractions are
    run sequentially.
    Here, for clarity raisons, what will happen :
    1) Extract a list of keyword to search inside offer from
    the database in workdir (`-w`) ;
    2) Connect to selected websites and parse listing to extract
    offers ;
    3) For each offer, this program will fetch offer's url and
    download webpage content (file / html) inside a temporary
    folder. Then, keywords are search inside the content of
    the offer. If `-d`, the file is saved in the workdir (`-w`);
    4) Geopy is used to find the geographic coordinates
    of the location associated with a job posting. This step
    might be skipped if the location associated with a job posting
    is already stored in the database;
    5) Job offer is exported to the database ;
    """
    # Ensure we have contact information
    if not contact:
        contact = ask_contact(ctx.obj["workdir"])

    retry_webpage_fetch = max(retry_webpage_fetch, 0)
    reinspect_offer_after = max(reinspect_offer_after, 0)
    sleep_before_retry = max(sleep_before_retry, 0.25)

    if download:
        ebp = JobScrapperSkeleton.get_page_exporter(
            save_type=download,
            compress=compress_download,
        )
    else:
        ebp = None

    for scrapper_name in scrappers:
        scrapper = SCRAPER_REGISTRY[scrapper_name]

        scrapper.run(
            contact=f"{contact}-(Running job-scrapper {scrapper_name})",
            page_exporter=ebp,

            sql_export=True,
            tsv_export=tsv,

            search_offer_text=True,
            search_offer_html=True,
            keywords_to_search=None,

            retry_offer_fetch=retry_webpage_fetch,
            failed_sleep=sleep_before_retry,


            database_name=None,
            workdir=ctx.obj["workdir"],

            batch_export=batch_export,
            re_inspect_after=reinspect_offer_after,
        )
