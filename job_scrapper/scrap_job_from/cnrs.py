from typing import Iterator, Self

from bs4 import BeautifulSoup
from selenium.webdriver.remote.webelement import WebElement

from selenium.webdriver.support.ui import Select
from web_processing.enhanced_chrome_browser import EnhancedChrome
import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException

class CNRScrapper(srk.JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from CNR's website
    """

    HEADERS = [
        "post_date",  # "Date de parution",
        "title",
        "localisation",  # "Type poste",
        "general_localisation",
        "contract_type",
    ]

    @classmethod
    def get_offer_listing_url(cls) -> str:
        """
        Returns a url that lead to an online listing of offers.
        """
        return "https://emploi.cnrs.fr/RechercheAvancee.aspx"

    def get_expected_geopy_country_code(self) -> list[str | None]:
        return ["FR", None]
    #############################################
    #   START     listing iterator     START   #
    ############################################œ
    @classmethod
    def iter_trough_offer_listing(cls, url: str) -> Iterator["Self"]:
        """
        Iter through each pages of the online listing <get_offer_listing_url>.
        """
        return cls.get_web_processor().extract_block_across_multiple_pages_using_button_iterator(
              url,
              cls.iter_trough_pages
        )

    @classmethod
    def iter_trough_pages(cls, driver: EnhancedChrome) -> Iterator[WebElement | None]:
        cls.logger.debug("Loading '%s'", "Default region")
        yield None

        for region in cls.get_region_list(driver):
            # At each loop, we expect a new page to be loaded.
            # We need to find again our button / Dropdown
            dropdown_element = cls.identify_dropdown(driver)
            dropdown = Select(dropdown_element)
            search_button = cls.identify_search_buton(driver)

            # Set dropdown to 'region'

            dropdown.select_by_value(region)

            # Let cls.get_web_processor().extract_block_across_multiple_pages_using_button_iterator
            # Export current HTML page and load next regional listing using search_button
            cls.logger.debug("Loading '%s'", region)

            yield search_button

        # Theoretically, cls.get_web_processor().extract_block_across_multiple_pages_using_button_iterator
        # should export HTML page loaded during the last loop

    @classmethod
    def get_region_list(cls, driver: EnhancedChrome):
        dropdown_element = cls.identify_dropdown(driver)

        dropdown = Select(dropdown_element)
        options = dropdown.options

        return sorted(
            [
                str(opt.get_attribute("value"))
                for opt in options
                if opt.get_attribute("value") is not None
            ],
            reverse=True,
        )

    @classmethod
    def identify_dropdown(cls, driver: EnhancedChrome):
        # time.sleep(60)
        return driver.wait_until_clickable(
            selector=By.ID,
            element_id="DdlBassinsGeographiques",
            ignored_exceptions=(StaleElementReferenceException,)
        )

    @classmethod
    def identify_search_buton(cls, driver: EnhancedChrome):
        return driver.wait_until_clickable(
            selector=By.ID,
            element_id="CphMain_BtnRecherche",
            ignored_exceptions=(StaleElementReferenceException,)
        )
    ############################################
    #   END       listing iterator       END   #
    ############################################
    def get_expected_download_time(self) -> int:
        """If offers on the scrapped website are contained inside files
        (pdf ...), the file should be downloaded.
        This function says how long the download is expected to take.
        Returns -1 if no download (file) is expected."""
        return -1

    @classmethod
    def find_offer_listing_on_page(cls, soup: BeautifulSoup) -> BeautifulSoup:
        """Should return a BeautifulSoup that only contains the offer listing.
        (This soup should not contain webpage header / footer other metadata.)
        """
        return soup.find(
            name="tbody",
        )

    @classmethod
    def generate_offer_from_listing(cls, soup: BeautifulSoup) -> Iterator[Self]:
        """Generate a number of scrapper object from a block of HTML code that
        should correspond to the listing of offers.
        """
        for tr in soup.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]

            # Ignore empty cell
            if not cells:
                continue

            kwargs = dict(zip(cls.HEADERS, cells))

            # Find url
            url = cls.get_website_base_url() + str(tr.find("a")["href"])

            # Generate job
            yield cls(url=url, **kwargs)

if __name__ == "__main__":
    import sys

    main_class = CNRScrapper
    if len(sys.argv) < 2:
        raise IndexError(
            "This script expect one argument : Contact information.\n\n"
            "Please run this program (python 3 <file> <contact>) using your\n"
            "email as contact. This is mandatory to comply with Geopy terms\n"
            "of services. Your <contact> information will be transmitted to\n"
            "geopy and might be written inside (local) log file / terminal. "
            ""
        )

    # Keywords
    keywords_to_search = main_class.get_keyword_manager()
    keywords_to_search.add_regex("Informatics", "Informatique")
    keywords_to_search.add_regex("Informatics", "Informatics")
    keywords_to_search.add_regex("Localisations", "Paris, France")
    keywords_to_search.add_regex("Localisations", "Lyon, France")
    keywords_to_search.add_regex("Letters", "a")

    #
    main_class.run(
        contact=f"{sys.argv[1]}-{main_class.get_standardised_class_name()}",
        keywords_to_search=keywords_to_search,
        page_exporter=main_class.get_page_exporter(),
    )