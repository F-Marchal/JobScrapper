import os
import re
import hashlib
from typing import Self, Iterator

from geopy.distance import geodesic  # type: ignore[import-untyped]
from geopy.exc import GeocoderServiceError  # type: ignore[import-untyped]
from geopy.geocoders import Nominatim  # type: ignore[import-untyped]

from web_processing.enhanced_chrome_browser import EnhancedChrome
from enum import Enum

from urllib.parse import urlparse

from .sql_core import ScrapperSQLightCore, KeywordManager
from web_processing.block_extractor import WebBlockExtractor
from tools.turn_file_to_text import FileToText
from web_processing.export_browser_file import ExportBrowserPage
from tools.geolocalisation import Geolocalisation, Session, Places
from bs4 import BeautifulSoup

class ScrapperRequestCore(ScrapperSQLightCore):

    class URLInspectionTimeStamp(str, Enum):
        DOWNLOAD = "Download"
        KEYWORD = "Keyword Research"
        HTML = "HTML Research"
        TEXT = "Textual Research"

        def __str__(self):
            return self.value

    SaveTypes = ExportBrowserPage.SaveTypes
    metadata_download_folder = f"{URLInspectionTimeStamp.DOWNLOAD}_Folder"
    metadata_download_type = f"{URLInspectionTimeStamp.DOWNLOAD}_Type"

    ################################################################
    #                     Foreign tool class                       #
    ################################################################
    _web_processor: WebBlockExtractor | None = None
    _geolocator: Geolocalisation | None = None
    hide_web_driver = True

    @classmethod
    def get_web_processor(cls, *args, **kwargs) -> WebBlockExtractor[Self]:
        if cls._web_processor is None:
            cls._web_processor = cls.initialise_web_processor(*args, **kwargs)
        return cls._web_processor

    @classmethod
    def initialise_web_processor(cls, *args, **kwargs) -> WebBlockExtractor[Self]:
        if "hide_web_driver" not in kwargs:
            kwargs["hide_web_driver"] = cls.hide_web_driver

        if "default_page_preparation" not in kwargs:
            kwargs["default_page_preparation"] = cls.prepare_page

        return WebBlockExtractor(
            *args,
            block_extractor=cls.find_offer_listing_on_page,
            block_convertor=cls.generate_offer_from_listing,
            **kwargs,
        )

    @classmethod
    def get_geolocator(cls, contact: str | None = None, **kwargs) -> Geolocalisation:
        if cls._geolocator is not None:
            return cls._geolocator

        if contact is None:
            raise KeyError("Please provide a contact for geopy compliance.")

        cls._geolocator = Geolocalisation(
                contact=contact,
                logger=cls.logger,
                **kwargs
            )
        return cls._geolocator

    @classmethod
    def get_page_exporter(cls, save_type: SaveTypes = SaveTypes.MHTML, compress: bool = False) -> ExportBrowserPage:
        return ExportBrowserPage(
            save_type=save_type,
            compress=compress,
            logger=cls.logger
        )



    ################################################################
    #                  Surcharge  methods                          #
    ################################################################
    def __init__(self, *args, geolocator: Geolocalisation | str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(geolocator, Geolocalisation):
            self._geolocator = geolocator
        else:
            self._geolocator = self.get_geolocator(contact=geolocator)

    @property
    def geolocator(self):
        return self._geolocator

    def to_place_entry(
            self,
            session: Session,
    ) -> Places:
        lat, long = self._geolocator.geolocate(
            session,
            self.localisation,
            add_in_database=False,
            restrict_country_codes=self.get_expected_geopy_country_code()
        )
        return Places(
            localisation=self.localisation,
            latitude=lat,
            longitude=long,
        )

    @classmethod
    def prepare_page(cls, browser: EnhancedChrome):
        """Command run every time a page is opened in
        a browser. Use this function to ensure all text is in display
        or to close pop-ups"""
        browser.scroll_to_bottom()

    ################################################################
    #                      Main methods                            #
    ################################################################
    def offer_inspection(
            self,
            keywords_to_search: KeywordManager | None = None,
            page_exporter: ExportBrowserPage | None = None,
            search_offer_text: bool = True,
            search_offer_html: bool = True,
            retry: int = 2,
            failed_sleep: int = 5,
    ):
        web_processor = self.get_web_processor()

        with web_processor.start_browser_on( # Automatically enforce rate limitation
                self.url,
                retry=retry,
                failed_sleep=failed_sleep
        ) as browser:
            raw_file, text_file = self.download_offer_page(browser)

            if page_exporter is not None:
                page_exporter.export(
                    browser=browser,
                    final_dir=self.get_self_dir(),
                    raw_file=raw_file,
                    text_file=text_file,
                    new_name="snapshot",
                )
                self.add_time_stamps(self.URLInspectionTimeStamp.DOWNLOAD, self.now())
                rel_path = os.path.relpath(self.get_self_dir(), start=self.get_workdir())
                self.add_metadata(
                    self.metadata_download_folder,
                    rel_path
                )
                self.add_metadata(
                    self.metadata_download_type,
                    page_exporter.save_type
                )

            if keywords_to_search is not None:
                self.search_keywords_in_offer(
                    downloaded_text_page=text_file,
                    keywords_to_search=keywords_to_search,
                )

            if search_offer_text:
                self.search_in_text_offer(
                    text_file
                )

            if search_offer_html:
                self.search_in_html_offer(
                    raw_file
                )

    def download_offer_page(
        self,
        browser: EnhancedChrome,
    ) -> tuple[str, str]:
        """
        Returns two path that lead to :
            - The offer as it is on self.url (.html, .pdf, ...)
            - The offer as a .txt file (Text only).

        If self.url point to a file, you can use this function as late as possible
        in your processing since EnhancedBrowser is supposed to download it in the background.
        /!\\ If the download already ended, make sure the file still exist and has not been
        renamed / removed / displaced."""
        self.add_time_stamps(str(self.URLInspectionTimeStamp.DOWNLOAD), self.now())

        # Wait for file download
        if self.url_point_to_file():
            raw_file: str = browser.wait_for_file_download_completion(
                timeout=self.get_expected_download_time(),
                url=self.url,
            )

        else:
            self.prepare_page(browser)
            raw_file: str = browser.save_raw_html()
        text_file = raw_file + ".txt"
        FileToText.convert_to_text_file(raw_file, text_file)

        return raw_file, text_file

    def search_keywords_in_offer(
            self,
            downloaded_text_page: str,
            keywords_to_search: KeywordManager,
    ):
        """Will erase all keyword count made previously for keywords in keywords_to_search"""
        self.add_time_stamps(str(self.URLInspectionTimeStamp.KEYWORD), self.now())
        keyword_pattern = keywords_to_search.keyword_patterns

        # I choose to use a dictionary instead of calling
        # retrieve / set keyword count for each loop
        result_dict = {
            keyword: 0 for keyword in keyword_pattern
        }

        # Read offer content
        with open(downloaded_text_page, "r") as file:
            for line in file:
                for keyword, pattern in keyword_pattern.items():
                    result_dict[keyword] += len(re.findall(pattern, line))

        # Read attributes:
        for keyword, pattern in keyword_pattern.items():
            result_dict[keyword] += len(re.findall(pattern, self.title)) * 10
            result_dict[keyword] += len(re.findall(pattern, self.field)) * 10
            result_dict[keyword] += len(re.findall(pattern, self.contract_type)) * 5
            result_dict[keyword] += len(re.findall(pattern, self.localisation)) * 2

        # Apply result_dict
        for keyword, count in result_dict.items():
            if len(keywords_to_search.regexes(keyword)) == 0:
                # This keyword is known to have 0 regex
                # attached. The result will always be 0.
                # This situation should be considered
                # as 'This keyword existed in the past
                # but has been discarded'. If the keyword
                # is still in the database it is for
                # traceability reasons.
                continue
            self.add_keyword_count(keyword, count)

    def search_in_html_offer(
            self,
            downloaded_html_page: str,
    ):
        self.add_time_stamps(str(self.URLInspectionTimeStamp.HTML), self.now())
        ...

    def search_in_text_offer(
            self,
            downloaded_text_page: str,
    ):
        self.add_time_stamps(str(self.URLInspectionTimeStamp.TEXT), self.now())
        ...


    @classmethod
    def extract_offers_from_website(
            cls,
            ensure_url_uniqueness: bool = True,
    ) -> Iterator["Self | None"]: # None to signifie that an offer has been ignored
        """
        Interrogate the website url returned in <cls.get_website_url()>
        to extract job offers.
        --> None : An offer has been ignored
        --> Self : An offer has been generated
        """
        cls.logger.info("Fetching offers from %s", cls.get_offer_listing_url())
        known_urls = set()

        i = 0
        for i, offers in enumerate(cls.iter_trough_offer_listing(cls.get_offer_listing_url())):
            if ensure_url_uniqueness:
                if offers.url in known_urls:
                    cls.logger.warning("Ignore offers #%s because of url collision ('%s').", i+1, offers.url)
                    yield None
                    continue

                known_urls.add(offers.url)

            if (i + 1) % 5 == 0:
                cls.logger.info(
                    "%s offers fetched from %s. Loop still in progress",
                    i+1,
                    cls.get_offer_listing_url()
                )

            known_urls.add(offers.url)

            yield offers

        cls.logger.info("%s offers fetched from %s. Loop finished.", i + 1, cls.get_offer_listing_url())
    ################################################################
    #                     Tools functions                          #
    ################################################################
    def url_point_to_file(self) -> bool:
        # Does self.url is expected to point on a file
        return self.get_expected_download_time() >= 0

    @classmethod
    def get_website_base_url(cls):
        return cls.extract_baseurl(cls.get_offer_listing_url())

    @staticmethod
    def extract_baseurl(url: str):
        """Extract the base url of a url."""
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        return base_url

    @classmethod
    def get_class_dir(cls):
        class_dir = os.path.join(cls.get_workdir(), cls.get_standardised_class_name())
        class_dir = os.path.abspath(class_dir)
        if not os.path.isdir(class_dir):
            cls.logger.debug("Make dir as it does not exist: %s", class_dir)
            os.mkdir(class_dir)

        return class_dir

    def get_self_dir(self) -> str:
        title = self.title.lower()
        title = re.sub(r'[^a-zA-Z0-9_-]+', '-', title)
        title = re.sub(r'-+', '-', title).strip('-')

        class_dir = self.get_class_dir()
        url = self.hash_text(self.url)[0:6]

        if not self.field:
            field = "Unknown"
        else:
            field = self.field
        field = re.sub(r'[^a-zA-Z0-9_-]+', '-', field)
        field = re.sub(r'-+', '-', field).strip('-')

        folder_name = f"{field[0:10]}-{title[0:20]}-{url}"

        self_dir = os.path.join(class_dir, folder_name)

        if not os.path.isdir(self_dir):
            self.logger.debug("Makedir as it does not exist: %s", self_dir)
            os.mkdir(self_dir)

        return self_dir

    @staticmethod
    def hash_text(text: str):
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    ################################################################
    # Prepare 'Questions' that should be answered by all scrappers #
    ################################################################
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

    def get_expected_geopy_country_code(self) -> list[str | None]:
        """Returns a list of country code that can help geopy / Nominatim
        to figure the right coordinate of self.localisation.
        You can use ISO 3166-1 alpha-2 country codes
        (https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2#Officially_assigned_code_elements)

        Geopy will only search inside country code that are listed here. You can use
        `None` in the returned list to search without geographic restrictions.

        return ["FR", None] --> Search in France then all around the world
        return ["FR", "UM"] --> Search in France then United States
        return ["FR", "UM", None] --> Search in France then United States then  all around the world
        """
        raise NotImplementedError