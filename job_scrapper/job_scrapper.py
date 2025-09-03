"""
Skeleton for JobScrapperClass
"""

import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options

from .logger import CoreLogger


# pylint: disable=R0902
# This is what I need to correctly describe a job offer.
# pylint: disable=R0913
# pylint: disable=R0917
# This is what I need to correctly set my attributes.
class JobScrapperSkeleton(CoreLogger):
    """
    Skeleton for JobScrapperClass. Those class should be able to :
    - Represent a job offer
    - Scrap a website to extract job offer
    - Parse job offer url to find more intel on the offer
    - Compute a distance between a location and the offer
    """

    website_url = ""
    across_multiple_pages = False
    sleep_between_job_interrogation = 2
    sleep_during_loading_period = 2
    sleep_before_retry_job_interrogation = 5

    selenium_chrome_options = Options()
    selenium_chrome_options.add_argument(
        "--headless"
    )  # Run chrome in headless mode (no window)

    def __init__(
        self,
        title: str,
        localisation: str | None,
        url: str,
        contract_type: str | None,
        field: str | None,
        **metadata,
    ):

        self.field = field
        self.contract_type = contract_type
        self.url = url
        self.localisation = localisation
        self.title = title
        self._fetch_date = time.localtime()
        self._metadata = metadata

        self._distances: dict[str, float] = {}
        self._keywords: dict[str, int] = {}

    # --- --- --- --- Export managements --- --- --- ----
    default_header = [
        "#Fetch Time",
        "Origin",
        "Localisation",
        "Field",
        "Contract",
        "Title",
        "Metadata",
        "Url",
    ]

    def flat(self, sep="\t", with_header=True) -> str:
        """
        Transform an offer to a line inside a flatfile.
        Since the header can vary due to configuration differences, you
            can choose if you want to get the header.

        :param str sep: a separator for the flat file ("\t", ",", ";", ...) Do not use "|" or "=" .
        :param bool with_header: Do the first line contain the header of this offer.
            Behind the scenes, the header is generated even with with_header=False. Due
            to this, with_header=False does not really improve method's speed.
        """
        metadata = []
        for pairs in self._metadata.items():
            metadata.append("=".join(pairs))

        items = [
            time.strftime("%Y-%m-%d %H:%M:%S", self._fetch_date),
            self.__class__.__name__,
            self.localisation,
            self.field,
            self.contract_type,
            self.title,
            "|".join(metadata),
            self.url,
        ]

        header = [*self.default_header]

        for keywords, occurrences in self._keywords.items():
            header.append(keywords + "(#)")
            items.append(str(occurrences))

        for places, distances in self._distances.items():
            header.append(places + " (km)")
            items.append(str(distances))

        str_items = sep.join(items)
        str_header = sep.join(header)

        if with_header:
            return f"{str_header}\n{str_items}"
        return str_items

    # --- --- --- --- Export managements --- --- --- ----
    # --- --- --- --- Job acquisition --- --- --- ----
    # --- --- Retrieve jobs  --- ---
    @classmethod
    def interrogate_website(cls) -> list["JobScrapperSkeleton"]:
        """
        Interrogate the website stored in <cls.website_url> to extract job offers.
        :return: All jobs offers founds in this website.
        """
        offers: list["JobScrapperSkeleton"] = []
        if cls.website_url == "":
            raise ValueError("<website_url> class variable is empty.")

        if cls.across_multiple_pages:
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
    def rough_page_parsing(cls, url: str, only_block_of_interest: bool = True):
        """
        Parse web page's html and return a block of html
        that correspond to the <cls.block_of_interest>
        :param bool only_block_of_interest: Does this function only returns
            the "block_of_interest" ?
        :param url: url that lead to the page to parse
        :return: A html soup that represent the <cls.block_of_interest> extracted from the url
        """

        cls.logger.debug("Starting Chrome on %s", url)
        browser = webdriver.Chrome(options=cls.selenium_chrome_options)
        try:
            browser.get(url)
        except WebDriverException as web_error:
            cls.logger.warning(web_error)
            time.sleep(cls.sleep_before_retry_job_interrogation)
            browser.get(url)

        cls._rough_page_parsing_actions(browser)
        time.sleep(cls.sleep_between_job_interrogation)

        html = browser.page_source
        browser.close()
        cls.logger.debug("Closing Chrome (%s)", url)

        soup = BeautifulSoup(html, "html.parser")

        if only_block_of_interest:
            return cls.extract_block_of_interest(soup)
        return soup

    @classmethod
    def _rough_page_parsing_actions(cls, browser):
        browser.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )
        time.sleep(cls.sleep_during_loading_period)

    @classmethod
    def extract_block_of_interest(cls, soup) -> BeautifulSoup:
        """
        Extract a block of html that contain the job offers.
        """
        raise NotImplementedError("Should be reimplemented when inherited")

    @classmethod
    def complete_job_page_parsing(
        cls,
        offers: list["JobScrapperSkeleton"],
        soup,
    ):
        """Scrap <cls.website_url> to find a number of job offer.
        Those job offer are stored inside 'offers'.
        :param offers: A list of job offer
        :param soup: A Beautiful soup object (html)
        :return:
        """
        raise NotImplementedError("Should be reimplemented when inherited")

    # --- --- Retrieve jobs  --- ---
    # --- --- Analyse jobs  --- ---
    @classmethod
    def analyse_jobs(
        cls,
        *jobs: "JobScrapperSkeleton",
        localisations: list[str] | None = None,
        keywords: dict[str, list[str]] | None = None,
    ):
        """
        Try to scrap a maximum of details from an offer.
        :param jobs: A number of Job object
        :param list[str] localisations: A list of places. The distances between
            those places and the offer will be estimated.
        :param dict[str, list[str]] keywords: A dictionary of keywords. Each
            keyword is searched inside the offer a counted.
        """

        for job_object in jobs:
            if localisations:
                job_object.compute_localisation(*localisations)

            if keywords:
                job_object.search_keywords(**keywords)

    def compute_localisation(self, *localisations: str):
        """Compute the distances between a number of location and
        this job offer.
        Results are stored inside <self._distances>"""
        raise NotImplementedError("Should be reimplemented when inherited")

    def search_keywords(self, **keywords: list[str]):
        """
        Search a set of keywords with a number of aliases inside.
        This research is not case-sensitive.
        the page pointed by <self.url>.
        Results are stored inside <self.keywords>
        key=["key", "alias1", "alias2"]
        """
        raise NotImplementedError("Should be reimplemented when inherited")

    # --- --- Analyse jobs  --- ---
    # --- --- --- --- Job acquisition --- --- --- ----
    # --- --- --- --- Attributes managements --- --- --- ----
    @staticmethod
    def clean_string(string: str | None) -> str | None:
        """
        Clean a string by stripping it, replacing every "\t" and "\n" by " " and by
        removing consecutive spaces. Spacing are replaced by "_".
        :param string: A string that should be cleaned
        :return str: The new string
        """
        if string is None:
            return None

        string = string.strip()
        string = string.replace("\n", " ").replace("\t", " ")

        while "  " in string:
            string = string.replace("  ", " ")
        return string.strip().title()

    # --- --- title --- ----
    @property
    def title(self) -> str:
        """Returns the title of this job"""
        return str(self._title)

    @title.setter
    def title(self, value: str | None):
        """Set the title of this job"""
        self._title = self.clean_string(value)

    # --- --- localisation --- ----
    @property
    def localisation(self) -> str:
        """Returns the location of this job"""
        return str(self._localisation)

    @localisation.setter
    def localisation(self, value: str | None):
        """Set the localisation of this job. Use an addresses or
        a geographic landmark"""
        self._localisation = self.clean_string(value)

    # --- --- url --- ----
    @property
    def url(self) -> str:
        """Returns the url that contain more details on this offer"""
        return str(self._url)

    @url.setter
    def url(self, value: str):
        """Set the url that contain more details on this offer"""
        self._url = self.clean_string(value)

    # --- --- contract_type --- ----
    @property
    def contract_type(self) -> str:
        """Returns the contract type (CDI, CDD, Internship...)"""
        return str(self._contract_type)

    @contract_type.setter
    def contract_type(self, value: str | None):
        """Set the contract type (CDI, CDD, Internship...)"""
        self._contract_type = self.clean_string(value)

    # --- --- contract_type --- ----
    @property
    def field(self) -> str:
        """Returns the field of this offer (Bioinformatics, biology, management...)"""
        return str(self._field)

    @field.setter
    def field(self, value: str | None):
        """Set the field of this offer (Bioinformatics, biology, management...)"""
        self._field = self.clean_string(value)

    # --- --- metadata --- ----
    @property
    def metadata(self) -> dict[str, str]:
        """Returns a copy of all metadata"""
        return self._metadata.copy()

    # --- --- fetch_date --- ----
    @property
    def fetch_date(self) -> time.struct_time:
        """Returns a time.struct_time theoretically generated when the job was fetched"""
        return self._fetch_date

    # --- --- distances --- ----
    @property
    def distances(self) -> dict[str, float]:
        return self._distances.copy()

    # --- --- keywords --- ----
    @property
    def keywords(self) -> dict[str, int] :
        return self._keywords.copy()

    # --- --- --- --- Attributes managements --- --- --- ----
