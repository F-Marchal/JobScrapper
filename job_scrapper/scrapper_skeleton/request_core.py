import os
import re
import tempfile
import time
import zipfile
from typing import Callable
from urllib.parse import urlparse
from selenium.common.exceptions import (
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import bs4
from bs4 import BeautifulSoup
from geopy.distance import geodesic  # type: ignore[import-untyped]
from geopy.exc import GeocoderServiceError  # type: ignore[import-untyped]
from geopy.geocoders import Nominatim  # type: ignore[import-untyped]
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options

from .object_core import ScrapperObjectCore


class ScrapperRequestCore(ScrapperObjectCore):
    """
    Specialisation of ScrapperObjectCore. Add the ability to fetch
    website's jobs, count keywords occurrences inside the description
    of an offer and compute distances between two localisation
    (e.g. job' address and a city)
    """

    website_url = ""
    job_across_multiple_pages = False
    job_across_multiple_pages_mandatory_action = False

    sleep_between_job_interrogation = 2
    sleep_between_keyword_interrogation = 4

    sleep_during_page_loading = 2
    sleep_before_retry_job_interrogation = 5
    timeout_close_pop_up = 3

    selenium_chrome_options = Options()
    selenium_chrome_options.add_argument(
        "--headless"
    )  # Run chrome in headless mode (no window)

    # pylint: disable=R1732
    # This tempdir should always remain open
    sleep_before_retry_downloading = 15
    sleep_between_downloading = 4
    download_temp_dir = tempfile.TemporaryDirectory()
    selenium_download_file_with_chrome_options = webdriver.ChromeOptions()
    selenium_download_file_with_chrome_options.add_argument(
        "--headless"
    )  # Run chrome in headless mode (no window)
    selenium_download_file_with_chrome_options.add_experimental_option(
        "prefs",
        {
            # Change default directory for downloads
            "download.default_directory": os.path.abspath(
                download_temp_dir.name
            ),
            # Auto download the file
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            # It will not show PDF directly in chrome
            "plugins.always_open_pdf_externally": True,
        },
    )

    sleep_between_geo_interrogation = 2
    sleep_before_geo_interrogation = 5
    geolocator = Nominatim(user_agent="JobScrapperSkeleton")
    geolocator_timeout = None

    # --- --- --- --- Job acquisition --- --- --- ----
    # --- --- Retrieve jobs  --- ---
    @classmethod
    def interrogate_website(
        cls, prepare_page: Callable | None = None
    ) -> list["ScrapperRequestCore"]:
        """
        Interrogate the website stored in <cls.website_url> to extract job offers.
        :return: All jobs offers founds in this website.
        """

        offers: list["ScrapperRequestCore"] = []
        if cls.website_url == "":
            raise ValueError("<website_url> class variable is empty.")

        cls.logger.info("Starting interrogation of %s", cls.website_url)

        if cls.job_across_multiple_pages_mandatory_action:
            for soups in cls._job_across_multiple_pages_command_action():
                html_block_of_interest = cls.extract_block_of_interest(soups)
                cls.complete_job_page_parsing(offers, html_block_of_interest)

        elif cls.job_across_multiple_pages:
            known_block = set()
            page_index = 1
            page_already_reached = False
            no_offer_in_last_page = False

            # Offers can be split between multiple pages.
            # An invalid page number load the first page.
            # This loop avoid offer duplication
            while not page_already_reached:
                url = cls.website_url.format(page=page_index)
                html_block_of_interest = cls.rough_page_parsing(
                    url, prepare_page=prepare_page
                )

                if html_block_of_interest in known_block:
                    # A : Yes, we have done a full loop, lets stop !
                    # Remember : Offers can be split between multiple pages.
                    # An invalid page number load the first page.
                    page_already_reached = True
                    cls.logger.debug("Page %s already reached. Quiting loop.", page_index)
                    continue

                # A : No, lets continue !
                known_block.add(html_block_of_interest)

                last_number_of_offer = len(offers)
                cls.complete_job_page_parsing(offers, html_block_of_interest)
                new_number_of_offer = len(offers)
                cls.logger.debug("Number of offers incremented from %s to %s", last_number_of_offer, new_number_of_offer)

                # Kill switch when each page without offer have a new html_block_of_interest
                # but does not contain offers
                if last_number_of_offer - new_number_of_offer == 0:
                    cls.logger.debug("Page %s contains no job !", page_index)
                    if no_offer_in_last_page:
                        page_already_reached = True
                        cls.logger.debug("Page %s and %s contains no job. Quiting loop.", page_index-1, page_index)
                    else:
                        no_offer_in_last_page = True
                else:
                    no_offer_in_last_page = False

                # Continue the loop
                page_index += 1

        else:
            html_block_of_interest = cls.rough_page_parsing(
                cls.website_url, prepare_page=prepare_page
            )
            cls.complete_job_page_parsing(offers, html_block_of_interest)

        return offers

    @classmethod
    def rough_page_parsing(
        cls,
        url: str,
        only_block_of_interest: bool = True,
        sleep_time: int | None = None,
        prepare_page: Callable | None = None,
    ) -> bs4.BeautifulSoup:
        """
        Parse web page's html and return a block of html
        that correspond to the <cls.block_of_interest>
        :param bool only_block_of_interest: Does this function only returns
            the "block_of_interest" ?
        :param url: url that lead to the page to parse
        :param int or None sleep_time: How long the function sleep. If None cls.sleep_between_job_interrogation is used.
        :param Callable prepare_page: A command that modify the page before parsing
        :return: A html soup that represent the <cls.block_of_interest> extracted from the url
        """

        browser = cls.open_url_inside_browser(url)

        if not callable(prepare_page):
            cls._rough_page_parsing_actions(browser)
        else:
            prepare_page(browser)

        if sleep_time is None:
            time.sleep(cls.sleep_between_job_interrogation)
        else:
            time.sleep(sleep_time)

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
                cls.logger.fatal(
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
    def _rough_page_parsing_actions(cls, browser) -> None:
        """
        A simple method called each time a page should be parsed.
        :param browser: A selenium browser
        """
        browser.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )
        time.sleep(cls.sleep_during_page_loading)

    @classmethod
    def _job_across_multiple_pages_command_action(cls) -> list[bs4.BeautifulSoup]:
        """Uses selenium to clik on button when we can not just use {page} in url.
        Returns a list of bs4.BeautifulSoup that correspond to a html page."""
        raise NotImplementedError("Should be reimplemented when inherited")

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

    @classmethod
    def _close_pop_up(cls, browser, button_identifier, by=By.CSS_SELECTOR, msg="Pop up"):
        try:
            pop_up = WebDriverWait(browser, cls.timeout_close_pop_up).until(
                EC.element_to_be_clickable(
                    (by, button_identifier)
                )
            )
            pop_up.click()
            cls.logger.debug("%s is closed.", msg)
        except TimeoutException:
            cls.logger.debug("%s not found.", msg)

    # --- --- Retrieve jobs  --- ---
    # --- --- Analyse jobs  --- ---
    # pylint: disable=R0913
    # Job analysis require a lot of configuration
    @classmethod
    def analyse_jobs(
        cls,
        *jobs: "ScrapperRequestCore",
        localisations: list[str] | None = None,
        keywords: dict[str, list[str]] | None = None,
        known_localisations: dict[str, tuple[float, float]] | None = None,
        known_urls: set[str] | None = None,
        save_job_page: bool = False,
    ) -> list["ScrapperRequestCore"]:
        """
        Try to scrap a maximum of details from an offer.
        :param jobs: A number of Job object
        :param list[str] localisations: A list of places. The distances between
            those places and the offer will be estimated.
        :param dict[str, list[str]] keywords: A dictionary of keywords. Each
            keyword is searched inside the offer a counted.
        :param dict[str, tuple[float, float]] known_localisations: A dictionary of
            known localisations : "localisation1": (latitude, longitude)
        :param set[str] or None known_urls: A set of url that should not be parsed.
            Each job object with its url in this set will be ignored.
        :param bool save_job_page: Do the webpage of this offer is download
            and stored on the disk ? Job's metadata will be updated to
            link file and object.
        """
        if known_localisations is None:
            known_localisations = {}
        if known_urls is None:
            known_urls = set()
        if keywords is None:
            keywords = {}

        cls.logger.info("Starting Analysis of %s jobs", len(jobs))
        cls.logger.debug("Analysis' <localisations> : %s", localisations)
        cls.logger.debug("Analysis' <known_localisations> : %s", known_localisations)
        cls.logger.debug("Analysis' <keywords> : %s", keywords)
        cls.logger.debug("Analysis' <known_urls> : %s", known_urls)
        cls.logger.debug("Analysis' <save_job_page> : %s", save_job_page)

        parsed_jobs = []

        for i, job_object in enumerate(jobs):
            if job_object.url in known_urls:
                cls.logger.info(
                    "%s / %s ignored. Its url is contained in <known_urls>.",
                    i,
                    len(jobs),
                )
                continue
            parsed_jobs.append(job_object)

            cls.logger.info("%s / %s analysis done.", i, len(jobs))
            known_urls.add(job_object.url)

            if localisations:
                job_object.compute_localisation(
                    *localisations, known_localisations=known_localisations
                )

            job_object.analyse_job_page(save_page=save_job_page, **keywords)

        return parsed_jobs

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
        if known_localisations is None:
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

    def analyse_job_page(self, save_page: bool = False, **keywords: list[str]):
        """
        Analyse job's webpage (self.url)
        :param bool save_page: Should we download this page and save it inside the workdir ?
        :param keywords: A number of keywords. Each keyword is searched inside the offer a counted.
        :return:
        """
        if not save_page and not keywords:
            # Nothing to do
            return

        page_content = self.rough_page_parsing(
            self.url,
            only_block_of_interest=False,
            sleep_time=self.sleep_between_keyword_interrogation,
        )

        if save_page:
            self.save_job_page(page_content)

        if keywords:
            self.search_keywords(page_content, **keywords)

    def _generate_job_file_name(self, ext: str | None=None) -> tuple[str, str]:
        """
        Generate a name (and a path) for when the content of self.url should be saved.
        This path will be self.workdir/self.get_class_name()/time self.title
        :param str ext: file extension (html; pdf ...)
        :return: Folder name and file name
        """
        local_time = time.localtime()
        formatted_time = time.strftime("%Y-%m-%d_%H:%M:%S", local_time)
        if ext:
            name = formatted_time + " " + self.title[:30] + f".{ext}"
        else:
            name = formatted_time + " " + self.title[:30]

        sanitized_name = re.sub(r'[<>"/\\|?*\x00-\x1F]', '', name)
        sanitized_name = sanitized_name.strip()

        folder = os.path.join(self.workdir, self.get_class_name())
        if not os.path.exists(folder):
            os.mkdir(folder)
        return folder, sanitized_name

    def save_job_page(self, page_content: bs4.BeautifulSoup, ext: str = "html"):
        """
        Use it to save the content of self.url inside a zip file. File path is selected by
        self._generate_job_file_name
        :param bs4.BeautifulSoup page_content: Content of self.url
        :param str ext: file extension (html; pdf ...)
        """
        self.time_stamps["page_download"] = time.localtime()

        folder, name = self._generate_job_file_name(ext)
        file_path = os.path.join(folder, name)
        file_path = self.get_unique_file_name(file_path, "zip")

        self.logger.debug("Saving job in %s", file_path)

        try:
            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(name, str(page_content))
        except FileNotFoundError as fne:
            self.logger.error("Unable to save '%s' as zip : %s", self.url, fne)

        # Reduce path length when possible
        if self.workdir in file_path:
            self._metadata["job_page"] = os.path.relpath(file_path, start=self.workdir)
        else:
            self._metadata["job_page"] = file_path

    def search_keywords(
        self, page_content: bs4.BeautifulSoup | str, **keywords: list[str]
    ):
        """
        Search a set of keywords with a number of aliases inside the page_content.
        This research is not case-sensitive.
        the page pointed by <self.url>.
        Results are stored inside <self.keywords>
        key=["key", "alias1", "alias2"]
        :param bs4.BeautifulSoup or str page_content: An html BeautifulSoup or a string
        """
        self.time_stamps["keywords_research"] = time.localtime()
        self._search_keyword_in_page_content(page_content, **keywords)
        self._search_keywords_in_attributes(**keywords)


    def _search_keywords_in_attributes(self, **keywords: list[str]):
        for key, list_of_associated_keywords in keywords.items():
            if key not in self._keywords:
                self._keywords[key] = 0

            for patterns in list_of_associated_keywords:
                count = len(re.findall(f"(?={patterns.lower()})", self.field.lower()))
                count += len(re.findall(f"(?={patterns.lower()})", self.contract_type.lower()))
                count += len(re.findall(f"(?={patterns.lower()})", self.localisation.lower()))
                count += len(re.findall(f"(?={patterns.lower()})", self.title.lower()))
                self._keywords[key] += count

    def _search_keyword_in_page_content(
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
            if key not in self._keywords:
                self._keywords[key] = 0

            for patterns in list_of_associated_keywords:
                count = len(re.findall(f"(?={patterns.lower()})", page_content))
                self._keywords[key] += count

    # --- --- Analyse jobs  --- ---
    # --- --- --- --- Job acquisition --- --- --- ----
