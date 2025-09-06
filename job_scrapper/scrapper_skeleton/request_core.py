import os
import re
import time
from urllib.parse import urlparse, unquote

import bs4
from bs4 import BeautifulSoup
from geopy.distance import geodesic  # type: ignore[import-untyped]
from geopy.exc import GeocoderServiceError  # type: ignore[import-untyped]
from geopy.geocoders import Nominatim  # type: ignore[import-untyped]
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options

from .object_core import ScrapperObjectCore
import tempfile
from PyPDF2 import PdfReader

class ScrapperRequestCore(ScrapperObjectCore):
    """
    Specialisation of ScrapperObjectCore. Add the ability to fetch
    website's jobs, count keywords occurrences inside the description
    of an offer and compute distances between two localisation
    (e.g. job' address and a city)
    """

    website_url = ""
    job_across_multiple_pages = False

    sleep_between_job_interrogation = 2
    sleep_between_keyword_interrogation = 4

    sleep_during_page_loading = 2
    sleep_before_retry_job_interrogation = 5

    selenium_chrome_options = Options()
    selenium_chrome_options.add_argument(
        "--headless"
    )  # Run chrome in headless mode (no window)

    sleep_before_retry_downloading = 15
    sleep_between_downloading = 4
    download_temp_dir = tempfile.TemporaryDirectory()
    selenium_download_file_with_chrome_options = webdriver.ChromeOptions()
    selenium_download_file_with_chrome_options.add_argument(
        "--headless"
    )  # Run chrome in headless mode (no window)
    selenium_download_file_with_chrome_options.add_experimental_option('prefs', {
        # Change default directory for downloads
        "download.default_directory": os.path.abspath(download_temp_dir.name),
        # Auto download the file
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        # It will not show PDF directly in chrome
        "plugins.always_open_pdf_externally": True
    })

    sleep_between_geo_interrogation = 2
    sleep_before_geo_interrogation = 5
    geolocator = Nominatim(user_agent="JobScrapperSkeleton")
    geolocator_timeout = None

    # --- --- --- --- Job acquisition --- --- --- ----
    # --- --- Retrieve jobs  --- ---
    @classmethod
    def interrogate_website(cls) -> list["ScrapperRequestCore"]:
        """
        Interrogate the website stored in <cls.website_url> to extract job offers.
        :return: All jobs offers founds in this website.
        """

        offers: list["ScrapperRequestCore"] = []
        if cls.website_url == "":
            raise ValueError("<website_url> class variable is empty.")

        cls.logger.info("Starting interrogation of %s", cls.website_url)

        if cls.job_across_multiple_pages:
            known_block = set()
            page_index = 1
            page_already_reached = False

            # Offers can be split between multiple pages.
            # An invalid page number load the first page.
            # This loop avoid offer duplication
            while not page_already_reached:
                url = cls.website_url.format(page=page_index)
                html_block_of_interest = cls.rough_page_parsing(url)

                if html_block_of_interest in known_block:
                    # A : Yes, we have done a full loop, lets stop !
                    # Remember : Offers can be split between multiple pages.
                    # An invalid page number load the first page.
                    page_already_reached = True
                    continue

                # A : No, lets continue !
                known_block.add(html_block_of_interest)

                cls.complete_job_page_parsing(offers, html_block_of_interest)

                # Continue the loop
                page_index += 1

        else:
            html_block_of_interest = cls.rough_page_parsing(cls.website_url)
            cls.complete_job_page_parsing(offers, html_block_of_interest)

        return offers

    @classmethod
    def rough_page_parsing(
        cls,
        url: str,
        only_block_of_interest: bool = True,
        sleep_time: int | None = None,
    ) -> bs4.BeautifulSoup:
        """
        Parse web page's html and return a block of html
        that correspond to the <cls.block_of_interest>
        :param bool only_block_of_interest: Does this function only returns
            the "block_of_interest" ?
        :param url: url that lead to the page to parse
        :param int or None sleep_time: How long the function sleep. If None cls.sleep_between_job_interrogation is used.
        :return: A html soup that represent the <cls.block_of_interest> extracted from the url
        """

        browser = cls.open_url_inside_browser(url)

        cls._rough_page_parsing_actions(browser)
        if sleep_time is None:
            time.sleep(cls.sleep_between_job_interrogation)

        html = browser.page_source
        browser.close()
        cls.logger.debug("Closing Chrome (%s)", url)

        soup = BeautifulSoup(html, "html.parser")

        if only_block_of_interest:
            return cls.extract_block_of_interest(soup)
        return soup

    @classmethod
    def open_url_inside_browser(cls, url: str, retry=2) -> webdriver.Chrome:
        """
        Create a new webdriver.Chrome that load <url>
        :param  str url: An url
        :param int retry: How many times this loading can be retried.
        :return: the webdriver.Chrome
        """
        cls.logger.debug("Starting Chrome on %s", url)
        browser = webdriver.Chrome(options=cls.selenium_chrome_options)
        try:
            browser.get(url)
        except WebDriverException as exception:
            cls.logger.warning("%s\n%s retry left", exception, retry)
            if retry <= 0:
                cls.logger.error(
                    "Multiple exception during interrogation of %s. \n%s",
                    url,
                    exception,
                )
                raise exception
            time.sleep(cls.sleep_before_retry_job_interrogation)
            retry -= 1
            return cls.open_url_inside_browser(url, retry)
        return browser

    @classmethod
    def _rough_page_parsing_actions(cls, browser):
        browser.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )
        time.sleep(cls.sleep_during_page_loading)

    @classmethod
    def extract_block_of_interest(cls, soup) -> BeautifulSoup:
        """
        Extract a block of html that contain the job offers.
        """
        raise NotImplementedError("Should be reimplemented when inherited")

    @classmethod
    def complete_job_page_parsing(
        cls,
        offers: list["ScrapperRequestCore"],
        soup,
    ):
        """Scrap <cls.website_url> to find a number of job offer.
        Those job offer are stored inside 'offers'.
        :param offers: A list of job offer
        :param soup: A Beautiful soup object (html)
        :return:
        """
        raise NotImplementedError("Should be reimplemented when inherited")

    @staticmethod
    def extract_baseurl(url: str):
        """Extract the base url of a url."""
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        return base_url

    @classmethod
    def get_base_url(cls):
        """Get class base url"""
        return cls.extract_baseurl(cls.website_url)

    # --- --- Retrieve jobs  --- ---
    # --- --- Analyse jobs  --- ---
    @classmethod
    def analyse_jobs(
        cls,
        *jobs: "ScrapperRequestCore",
        localisations: list[str] | None = None,
        keywords: dict[str, list[str]] | None = None,
        known_localisations: dict[str, tuple[float, float]] | None = None,
    ):
        """
        Try to scrap a maximum of details from an offer.
        :param jobs: A number of Job object
        :param list[str] localisations: A list of places. The distances between
            those places and the offer will be estimated.
        :param dict[str, list[str]] keywords: A dictionary of keywords. Each
            keyword is searched inside the offer a counted.
        :param dict[str, tuple[float, float]] known_localisations: A dictionary of
            known localisations : "localisation1": (latitude, longitude)
        """
        if not known_localisations:
            known_localisations = {}

        cls.logger.info("Starting Analysis of %s jobs", len(jobs))
        if not known_localisations:
            known_localisations = {}

        for i, job_object in enumerate(jobs):
            if i % 25:
                cls.logger.info("%s / %s analysis done.", i + 1, len(jobs))

            if localisations:
                job_object.compute_localisation(
                    *localisations, known_localisations=known_localisations
                )

            if keywords:
                job_object.search_keywords(**keywords)

    @classmethod
    def ask_for_localisation_coordinates(
        cls,
        localisation: str,
        known_localisations: dict[str, tuple[float, float]] | None = None,
        retry=2,
    ) -> tuple[float, float] | None:
        """
        Use geopy to determine the coordinate of a <localisation>. If this localisation
        is known (e.g. in <known_localisations>), this function will return
        <known_localisations>[<localisation>]. If this localisation
        is unknown, <known_localisations> is updated.
        :param str localisation: an address.
        :param dict[str, tuple[float, float]] known_localisations: A dictionary of
            known localisations : "localisation1": (latitude, longitude)
        :param retry: How many times this action will be retried in case of an error.
        :return: (geocode_objet.latitude, geocode_objet.longitude) or None if too many
            errors happen or if this address is unknown
        """
        if not known_localisations:
            known_localisations = {}

        if localisation in known_localisations:
            # This part ensure we do not make the same
            # request over and over
            cls.logger.debug(
                "'%s's coordinates are already known.", localisation
            )
            return known_localisations[localisation]

        try:
            cls.logger.debug("Asking for '%s' coordinates.", localisation)
            geocode_objet = cls.geolocator.geocode(
                localisation, timeout=cls.geolocator_timeout
            )
        except GeocoderServiceError as exception:
            cls.logger.warning("%s\n%s left", exception, retry)
            time.sleep(cls.sleep_before_geo_interrogation)

            if retry <= 0:
                return None
            retry -= 1
            return cls.ask_for_localisation_coordinates(
                localisation, known_localisations, retry
            )

        if not geocode_objet:
            return None

        result = (geocode_objet.latitude, geocode_objet.longitude)
        known_localisations[localisation] = result
        return result

    def compute_localisation(
        self,
        *localisations: str,
        known_localisations: dict[str, tuple[float, float]] | None = None,
    ):
        """Compute the distances between a number of location and
        this job offer.
        Results are stored inside <self._distances>"""
        if not localisations:
            return

        if not self._localisation or not (
            self_coord := self.ask_for_localisation_coordinates(
                self._localisation, known_localisations
            )
        ):
            self.logger.debug(
                "Can not find coordinates of %s", self._localisation
            )
            self._distances.update({key: -1 for key in localisations})
            return

        self.logger.debug(
            'Seeking distances between "%s" %s and "%s"',
            self._localisation,
            self_coord,
            " and ".join(localisations),
        )

        for positions in localisations:
            coord_positions = self.ask_for_localisation_coordinates(
                positions, known_localisations
            )

            distance = geodesic(coord_positions, self_coord).km

            self._distances[positions] = distance

            time.sleep(self.sleep_between_geo_interrogation)

    def search_keywords(self, **keywords: list[str]):
        """
        Search a set of keywords with a number of aliases inside.
        This research is not case-sensitive.
        the page pointed by <self.url>.
        Results are stored inside <self.keywords>
        key=["key", "alias1", "alias2"]
        """
        page_content = self.rough_page_parsing(
            self.url,
            only_block_of_interest=False,
            sleep_time=self.sleep_between_keyword_interrogation,
        )
        return self._job_page_content(page_content, **keywords)

    def _job_page_content(
        self, page: bs4.BeautifulSoup | str, **keywords: list[str]
    ):
        """
        Search a set of keywords with a number of aliases inside.
        This research is not case-sensitive.
        the page pointed by <self.url>.
        Results are stored inside <self.keywords>
        key=["key", "alias1", "alias2"]
        :param bs4.BeautifulSoup page_soup: An html beautifull soup.
        :param keywords: key=["key", "alias1", "alias2"]
        """
        if isinstance(page, bs4.BeautifulSoup):
            page_content = page.get_text().lower()
        else:
            page_content = page.lower()

        self.logger.debug("Seeking keywords in %s", self.url)
        for key, list_of_associated_keywords in keywords.items():
            self._keywords[key] = 0

            for patterns in list_of_associated_keywords:
                count = len(re.findall(f"(?={patterns.lower()})", page_content))
                self._keywords[key] += count

    # --- --- Analyse jobs  --- ---
    # --- --- Download files  --- ---
    @classmethod
    def download_file(cls, url: str, retry: int=2, timeout: int=360) ->  str | None:
        """
        Download a file using selenium
        :param str url: An url that point to a file
        :param int retry: Number of time that this action can be retried when
            an error occur
        :param int timeout: How long the download can last
        :return None or str: Path to the downloaded file when the download succeed. None otherise.
        """
        # https://stackoverflow.com/questions/43149534/selenium-webdriver-how-to-download-a-pdf-file-with-python

        download_dir = cls.download_temp_dir.name
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        filename = unquote(filename) # Avoid encoding errors
        filepath = os.path.join(download_dir, filename)
        
        cls.logger.debug("Downloading file : %s\ntimeout=%s\tExpected path : %s", url, timeout, filepath)
        driver = webdriver.Chrome(options=cls.selenium_download_file_with_chrome_options)
        
        try:
            driver.get(url)
            i = 0
            while not os.path.exists(filepath) and i < timeout:
                time.sleep(1)
                i += 1
    
        except WebDriverException as exception:
            cls.logger.warning("%s\n%s retry left", exception, retry)
            if retry <= 0:
                cls.logger.error(
                    "Multiple exception during interrogation of %s. \n%s",
                    url,
                    exception,
                )
                return None
            time.sleep(cls.sleep_before_retry_downloading)
            return cls.download_file(url)

        time.sleep(cls.sleep_between_downloading)

        if not os.path.exists(filepath):
            cls.logger.warning(f"Download failed : {filepath}")
            return None
        cls.logger.debug(f"Download completed : {filepath}")
        return filepath

    @staticmethod
    def parse_pdf(path: str) -> str:
        """Open a pdf in PdfReader"""
        pdf = PdfReader(path)
        output = []
        for pages in pdf.pages:
            output.append(pages.extract_text())

        return "\n\n\n\n".join(output)
    # --- --- Download files  --- ---
    # --- --- --- --- Job acquisition --- --- --- ----
