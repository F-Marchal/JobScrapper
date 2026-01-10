import re

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from bs4 import BeautifulSoup
from typing import Iterator, Self

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk
from job_scrapper.web_processing import EnhancedChrome

class SFBIScrapper(srk.JobScrapperSkeleton):
    """
    Use this file as a template to create your scrapper.
    """
    HEADERS = [
        "title",  # "Titre",
        "Niveau",
        "contract_type",  # "Type poste",
        "Contrat",
        "Durée",
        "Equipe",
        "localisation",  # "Lieu",
        "beginning",  # "Date début",
        "end",  # "Date fin",
        "Référence",
    ]
    ##########################################################
    #  mandatory customisation of website dependant methods  #
    ##########################################################
    @classmethod
    def get_offer_listing_url(cls) -> str:
        return "https://www.sfbi.fr/emplois/offres-en-cours"

    @classmethod
    def iter_trough_offer_listing(cls, url: str) -> Iterator["Self"]:
        return cls.get_web_processor().extract_block_across_multiple_pages_using_buttons(
              url,
              button_finder=cls.button_finder,
            wait_scroll_to_view_button=1,
        )

    @classmethod
    def button_finder(cls, browser: EnhancedChrome) -> WebElement | None:
        next_button = browser.wait_until_clickable(
            selector=By.CSS_SELECTOR,
            element_id="button.page-link.next",
        )
        is_disabled = next_button.get_attribute("aria-disabled")
        if is_disabled:
            return None
        return next_button

    def get_expected_download_time(self) -> int:
        return -1

    @classmethod
    def find_offer_listing_on_page(cls, soup: BeautifulSoup) -> BeautifulSoup:
        return soup.find(
            name="table",
        )


    @classmethod
    def generate_offer_from_listing(cls, soup: BeautifulSoup) -> Iterator[Self]:
        for tr in soup.find_all("tr"):
            # "tr" keyword indicate a table
            # "td" keyword indicate the end of a cell
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            kwargs = dict(zip(cls.HEADERS, cells))

            # Ignore empty cell
            if not cells:
                continue

            # Find url
            re_url = re.findall('<td.*><a href="(.*)"', str(tr))
            url = cls.get_website_base_url() + re_url[0]

            # Generate job
            yield cls(field="Bioinformatic", url=url, **kwargs)

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
        return ["FR", None]

if __name__ == "__main__":
    import sys

    main_class = SFBIScrapper
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