import os
import re
import hashlib
from typing import Self, Iterator

from geopy.distance import geodesic  # type: ignore[import-untyped]
from geopy.exc import GeocoderServiceError  # type: ignore[import-untyped]
from geopy.geocoders import Nominatim  # type: ignore[import-untyped]

from web_processing.enhanced_chrome_browser import EnhancedChrome
from enum import Enum

from .sql_core import ScrapperSQLightCore, KeywordManager
from web_processing.block_extractor import WebBlockExtractor
from tools.turn_file_to_text import FileToText
from web_processing.export_browser_file import ExportBrowserPage
from tools.geolocalisation import Geolocalisation, Session, Places

class ScrapperRequestCore(ScrapperSQLightCore):
    _web_processor: WebBlockExtractor = None

    class URLInspectionTimeStamp(Enum):
        DOWNLOAD = "Download"
        KEYWORD = "Keyword Research"
        HTML = "HTML Research"

    SaveTypes = ExportBrowserPage.SaveTypes
    @classmethod
    def make_page_exporter(cls) -> ExportBrowserPage:
        return ExportBrowserPage(
            save_type=cls.SaveTypes.MHTML,
            compress=False,
            logger=cls.logger
        )

    @classmethod
    def make_geolocator(cls, contact: str, **kwargs) -> Geolocalisation:
        return Geolocalisation(
            contact=contact,
            logger=cls.logger,
            **kwargs
        )

    ################################################################
    # Prepare 'Questions' that should be answered by all scrappers #
    ################################################################
    @classmethod
    def get_website_url(cls) -> str:
        """Returns website attached to cls. (The website that this crapper should scrap)"""
        raise NotImplementedError

    @classmethod
    def find_online_offers(cls, url: str) -> Iterator["Self"]:
        """Iter through the offer contained on cls.get_website_url """
        raise NotImplementedError

    @classmethod
    def initialise_web_processor(cls) -> WebBlockExtractor:
        """Method used to find the block of html code that
         contains offers on cls.get_website_url """
        raise NotImplementedError

    def get_expected_download_time(self) -> int:
        """If offers on the scrapped website are contained inside files
        (pdf ...), the file should be downloaded.
        This function says how long the download is expected to take.
        Returns -1 if no download (file) is expected."""
        raise NotImplementedError

    def __init__(self, *args, geolocator: Geolocalisation, **kwargs):
        super().__init__(*args, **kwargs)
        self._geolocator = geolocator

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
        )
        return Places(
            localisation=self.localisation,
            latitude=lat,
            longitude=long,
        )



    ################################################################
    #                                                              #
    ################################################################
    def url_point_to_file(self) -> bool:
        # Does self.url is expected to point on a file
        return self.get_expected_download_time() >= 0

    @classmethod
    def get_web_processor(cls) -> WebBlockExtractor:
        if cls._web_processor is None:
            cls._web_processor = cls.initialise_web_processor()
        return cls._web_processor

    # --- --- Retrieve jobs  --- ---
    @classmethod
    def extract_offers_from_website(
            cls,
            ensure_url_uniqueness: bool = True,
    ) -> Iterator["Self"]:
        """
        Interrogate the website url returned in <cls.get_website_url()>
        to extract job offers.
        """
        cls.logger.info("Fetching offers from %s", cls.get_website_url())
        known_urls = set()

        i = 0
        for i, offers in enumerate(cls.find_online_offers(cls.get_website_url())):
            if ensure_url_uniqueness:
                if offers.url in known_urls:
                    cls.logger.warning("Ignore offers #%s because of url collision ('%s').", i+1, offers.url)
                    continue

                known_urls.add(offers.url)

            if i % 25 == 0:
                cls.logger.info(
                    "%s offers fetched from %s. Loop still in progress",
                    i+1,
                    cls.get_website_url()
                )

            known_urls.add(offers.url)

            yield offers

        cls.logger.info("%s offers fetched from %s. Loop finished.", i + 1, cls.get_website_url())

    # --- --- Parse offer  --- ---
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

        with web_processor.start_browser_on(
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
                timeout=self.get_expected_download_time()
            )

        else:
            raw_file: str = browser.save_raw_html()
        text_file = raw_file + ".txt"
        FileToText.convert_to_text_file(raw_file, text_file)

        return raw_file, text_file

    def search_keywords_in_offer(
            self,
            downloaded_text_page: str,
            keywords_to_search: KeywordManager,
    ):
        self.add_time_stamps(str(self.URLInspectionTimeStamp.KEYWORD), self.now())
        keyword_pattern = keywords_to_search.keyword_patterns

        # I choose to use a dictionary instead of calling
        # retrieve / set keyword count for each loop
        result_dict = {
            keyword: self.retrieve_keyword_count(keyword) for keyword in keyword_pattern
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
            self.add_keyword_count(keyword, count)

    def search_in_html_offer(
            self,
            downloaded_html_page: str,
    ):
        pass

    def search_in_text_offer(
            self,
            downloaded_html_page: str,
    ):
        pass

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
        title = re.sub(r'[^a-z0-9_-]+', '-', title)  # remplace les caractères interdits
        title = re.sub(r'-+', '-', title).strip('-')  # évite les doublons

        class_dir = self.get_class_dir()
        url = self.hash_text(self.url)[0:6]

        if self.field:
            field = "Unknown"
        else:
            field = self.field

        folder_name = f"{field}-{title}-{url}"

        self_dir = os.path.join(class_dir, folder_name)

        if not os.path.isdir(self_dir):
            self.logger.debug("Make dir as it does not exist: %s", self_dir)
            os.mkdir(self_dir)

        return self_dir

    @staticmethod
    def hash_text(text: str):
        return hashlib.sha1(text.encode("utf-8")).hexdigest()




