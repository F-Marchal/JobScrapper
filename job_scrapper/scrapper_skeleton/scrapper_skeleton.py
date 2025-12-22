"""
Skeleton for JobScrapperClass
"""

import json
import os.path
from contextlib import contextmanager
from typing import Self, Iterator
from web_processing.block_extractor import WebBlockExtractor

import re
from .request_core import ScrapperRequestCore, KeywordManager, ExportBrowserPage, BeautifulSoup
from sql.tables.keywords.keyword_version import KeywordVersion


class JobScrapperSkeleton(ScrapperRequestCore):
    @classmethod
    def run(
            cls,
            contact: str,
            keywords_to_search: KeywordManager | None = None,
            page_exporter: ExportBrowserPage | None = None,
            tsv_export: bool = True,
            sql_export: bool = True,

            search_offer_text: bool = True,
            search_offer_html: bool = True,
            retry_offer_fetch: int = 2,
            failed_sleep: int = 5,

            batch_export: int = 20,
            database_name: str | None = None,
            workdir: str | None = None,
    ):
        if not database_name:
            database_name = cls.DEFAULT_DATABASE

        if not workdir:
            workdir = cls.get_workdir()

        # Initialize geolocalisator with a contact.
        cls.logger.info("Initialisation of geopy rate limiter... (%s)", contact)
        cls.get_geolocator(contact)

        # Keyword management
        with cls.get_sql_session(workdir=workdir, database_name=database_name) as session:
            if keywords_to_search is None:
                cls.logger.info("Using default keywords to search configuration : Loading database...")
                keywords_to_search = KeywordManager(logger=cls.logger)
                keywords_to_search.load_all(session)

            else:
                # Ensure that all keywords version exist in database.
                keywords_to_search.commit(session)

        with cls.get_sql_session(workdir=workdir, database_name=database_name) as session:
            keyword_ver = keywords_to_search.versions(session)

        cls.logger.info(
            "%s keyword(s) found : \n%s",
            len(keyword_ver), "\n".join([f"{k}: {v}" for k, v in keyword_ver.items()])
        )

        tsv_folder = os.path.join(cls.get_class_dir(), "TSVs")
        if not os.path.exists(tsv_folder):
            os.mkdir(tsv_folder)
        tsv_file = cls.get_unique_path(os.path.join(tsv_folder, f"{cls.strftime(cls.now())}.tsv"))

        # TODO: Batch export
        offer_batch = []
        for i, offers in enumerate(cls.extract_offers_from_website()):
            if offers is None:
                # An offer should be ignored see extract_offers_from_website logging.
                continue

            cls.logger.info("Processing offer %s : %s", i + 1, offers)
            cls.logger.debug("Proceeding to offer inspection of %s (%s)", offers, i + 1)
            offers.offer_inspection(
                keywords_to_search=keywords_to_search,
                page_exporter=page_exporter,
                search_offer_html=search_offer_html,
                search_offer_text=search_offer_text,
                retry=retry_offer_fetch,
                failed_sleep=failed_sleep,
            )
            offer_batch.append(offers)

            if len(offer_batch) >= batch_export:
                if sql_export:
                    cls._run_export_sql(
                        offer_batch=offer_batch,
                        database_name=database_name,
                        workdir=workdir,
                        i=i,
                        keywords_ver=keyword_ver,
                    )
                if tsv_export:
                    cls._run_export_tsv(
                        offer_batch=offer_batch,
                        i=i,
                        tsv_file=tsv_file,
                    )
                offer_batch.clear()

    def need_reinspection(
            self,
            delay: int,
            database_name: str | None = None,
            workdir: str | None = None,

            keywords_to_search: KeywordManager | None = None,
            page_exporter: ExportBrowserPage | None = None,
            tsv_export: bool = True,
            sql_export: bool = True,
    ):
        pass





    @classmethod
    def _run_export_tsv(
            cls,
            offer_batch: list[Self],
            i: int,
            tsv_file: str,
    ):

        offer_to_text = '\n'.join([f"{i - len(offer_batch) + oi} {o})" for oi, o in enumerate(offer_batch)])
        cls.logger.debug("Proceeding to sql exportation of %s offers :\n"
                         "%s",
                         len(offer_batch),
                         f"{offer_to_text}"
        )
        cls.export_to_flat_file(jobs=offer_batch, file_path=tsv_file, mod="a")

    @classmethod
    def _run_export_sql(
            cls,
            offer_batch: list[Self],
            database_name: str,
            workdir: str,
            i: int,
            keywords_ver: dict[str, KeywordVersion] | None = None


    ):
        offer_to_text = '\n'.join([f"{(i + 1) - len(offer_batch) + (oi + 1)} {o})" for oi, o in enumerate(offer_batch)])
        cls.logger.debug("Proceeding to sql exportation of %s offers :\n"
                         "%s",
                         len(offer_batch),
                         f"{offer_to_text}"
        )
        cls.sql_batch_export(
            *offer_batch,
            database_name=database_name,
            workdir=workdir,
            keywords_ver=keywords_ver,
        )

    # TOOLS
    @classmethod
    def try_to_find_field(cls, title: 'JobScrapperSkeleton | str'):
        """In those offers, the field is not always obvious to parse.
        This method tries to find it by parsing the title."""

        if isinstance(title, str):
            field = title
        else:
            field = title.title

        field = field.lower()
        if " - " in field:
            # Remove prefixes : "50238 - "; "IBODE -"
            field = " ".join(field.split(" - ")[1:])

        # Remove all link word
        link_words = [
            " en",     " de",     " à",      " pour",   " avec",    " sans",
            " sur",    " sous",   " dans",   " par",    " entre",   " chez",
            " vers",   " contre", " après",  " avant",  " depuis",  " pendant",
            " selon",  " malgré", " parmi",  " envers", " hors",    " sauf",
            " jusque", " via",    " et",     " ou",     " mais",    " donc",
            " or",     " ni",     " car",    " au",
        ]
        pattern = "|".join(re.escape(word) for word in link_words)
        field = re.sub(pattern, "", field)

        # The first two words generally gives
        # a good idea of the field
        field = " ".join(field.split(" ")[:2])

        # If the first world contains a dash
        # the first world is generally enough
        field = "-".join(field.split("-")[:2])

        return field


    # QUESTIONS

    @classmethod
    def get_offer_listing_url(cls) -> str:
        """Returns a url that lead to an online listing of offers."""
        raise NotImplementedError

    def get_expected_download_time(self) -> int:
        """If offers on the scrapped website are contained inside files
        (pdf ...), the file should be downloaded.
        This function says how long the download is expected to take.
        Returns -1 if no download (file) is expected."""
        raise NotImplementedError

    @classmethod
    def iter_trough_offer_listing(cls, url: str) -> Iterator["Self"]:
        """Iter through each pages of the online listing <get_offer_listing_url>.
        If you need to (re)write this method the simplest method are :

        When only one page is expected:
            - `cls.get_web_processor().extract_block_on_one_page(url)`

        When the url contains the page number :
            - `cls.get_web_processor().extract_block_across_multiple_pages_using_url(url)`

        When the url does not contain the page number:
            - `cls.get_web_processor().extract_block_across_multiple_pages_using_buttons(
                url,
                button_finder
            )`

            with `button_finder`:
                A. Function  (driver: "EnhancedChrome"() -> WebElement | None)
                    that find the button that can
                    be clicked to  load the next page. Generally a lambda
                    that trigger <browser.get_next_page_button>.
                B. Use a dictionary if you want to use <self.get_next_page_button>
                   as <button_finder>. In this case, make sure that the dict contains
                        - by: ByType,
                        - button_id: str,

        """
        raise NotImplementedError

    @classmethod
    def find_offer_listing_on_page(cls, soup: BeautifulSoup) -> BeautifulSoup:
        """Should return a BeautifulSoup that only contains the offer listing.
        (This soup should not contain webpage header / footer other metadata.)"""

        raise NotImplementedError

    @classmethod
    def generate_offer_from_listing(cls, soup: BeautifulSoup) -> Iterator[Self]:
        """Generate a number of scrapper object from a block of HTML code that
        should correspond to the listing of offers."""
        raise NotImplementedError

