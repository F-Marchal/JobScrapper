"""
Skeleton for JobScrapperClass
"""

import json
import os.path
from contextlib import contextmanager
from typing import Self, Iterator

from astroid import Raise

from web_processing.block_extractor import WebBlockExtractor

from .request_core import ScrapperRequestCore, KeywordManager, ExportBrowserPage, BeautifulSoup



class JobScrapperSkeleton(ScrapperRequestCore):
    @classmethod
    def run(
            cls,
            contact: str,
            keywords_to_search: KeywordManager | None = None,
            page_exporter: ExportBrowserPage | None = None,
            tsv_export: bool = True,

            search_offer_text: bool = True,
            search_offer_html: bool = True,
            retry_offer_fetch: int = 2,
            failed_sleep: int = 5,
    ):
        # Initialize geolocalisator with a contact.
        cls.logger.info("Initialisation of geopy rate limiter... (%s)", contact)
        cls.get_geolocator(contact)

        # Keyword management
        with cls.get_maindb_session() as session:
            if keywords_to_search is None:
                cls.logger.info("Using default keywords to search configuration : Loading database...")
                keywords_to_search = KeywordManager(logger=cls.logger)
                keywords_to_search.load_all(session)

            else:
                # Ensure that all keywords version exist in database.
                keywords_to_search.commit(session)

        with cls.get_maindb_session() as session:
            keyword_ver = keywords_to_search.versions(session)

        cls.logger.info(
            "%s keyword(s) found : \n%s",
            len(keyword_ver), "\n".join([f"{k}: {v}" for k, v in keyword_ver.items()])
        )

        tsv_folder = os.path.join(cls.get_class_dir(), "TSVs")
        if not os.path.exists(tsv_folder):
            os.mkdir(tsv_folder)
        tsv_file = cls.get_unique_path(os.path.join(tsv_folder, f"{cls.strftime(cls.now())}.tsv"))

        for i, offers in enumerate(cls.extract_offers_from_website()):
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

            cls.logger.debug("Proceeding to sql exportation of %s (%s)", offers, i + 1)
            with cls.get_maindb_session() as session:
                offers.sql_export(
                    session=session,
                    keywords_ver=keyword_ver,
                )

            if tsv_export:
                if i == 0:
                    tsv_line = offers.flat(with_header=True)
                else:
                    tsv_line = offers.flat(with_header=False)

                with open(tsv_file, "a", encoding="UTF-8") as file:
                    file.write(tsv_line)
                    file.write("\n")

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

