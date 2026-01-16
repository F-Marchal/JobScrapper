from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import StaleElementReferenceException

from bs4 import BeautifulSoup
from typing import Iterator, Self

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk
from job_scrapper.web_processing.enhanced_chrome_browser import EnhancedChrome

class SanofiScrapper(srk.JobScrapperSkeleton):
    """
    Use this file as a template to create your scrapper.
    """
    ##########################################################
    #  mandatory customisation of website dependant methods  #
    ##########################################################

    @classmethod
    def get_offer_listing_url(cls) -> str:
       return "https://jobs.sanofi.com/fr/recherche-d%27offres/France/2649/2/3017382/46/2/50/2"

    @classmethod
    def iter_trough_offer_listing(cls, url: str) -> Iterator["Self"]:
        return cls.get_web_processor().extract_block_across_multiple_pages_using_buttons(
              url,
              button_finder=cls.next_page_command,
              prepare_page=cls.prepare_page,
              wait_scroll_to_view_button=3,
        )

    @classmethod
    def next_page_command(cls, browser: EnhancedChrome) -> WebElement | None:
        try:
            browser.wait_until_clickable(
                By.CSS_SELECTOR,
                "a.next.disabled",
                ignored_exceptions=(StaleElementReferenceException,)
            )
            return None

        except TimeoutException:
            next_button = browser.wait_until_clickable(
               By.CSS_SELECTOR,
            "a.next",
                ignored_exceptions=(StaleElementReferenceException,)
            )

        return next_button

    @classmethod
    def prepare_page(cls, browser: EnhancedChrome) -> None:
        browser.safe_close_pop_up(
            selector=By.CSS_SELECTOR,
            button_id="button.onetrust-close-btn-handler.banner-close-button.ot-close-link",
        )
        super().prepare_page(browser)

    def get_expected_download_time(self) -> int:
        return  -1

    @classmethod
    def find_offer_listing_on_page(cls, soup: BeautifulSoup) -> BeautifulSoup:
        return soup.find(name="div", id="search-results-list")

    @classmethod
    def generate_offer_from_listing(cls, soup: BeautifulSoup) -> Iterator[Self]:
        for cells in soup.find_all("li"):
            url = cls.get_website_base_url() + str(cells.find("a")["href"])
            ref = str(cells.find("a")["data-job-id"])
            title = str(cells.find("h2").get_text(strip=True))
            localisation = str(
                cells.find("span", class_="job-location").get_text(strip=True)
            ).replace("Site:", "")
            field = str(
                cells.find("span", class_="job-category").get_text(strip=True)
            ).replace("Catégorie:", "")

            # pylint: disable=R0801
            # I do not see how to merge this part with other classes
            kwargs = {
                "field": field,
                "contract_type": None,
                "url": url,
                "localisation": localisation,
                "title": title,
                "reference": ref,
            }
            yield cls(**kwargs)

    def search_in_html_offer(
            self,
            downloaded_html_page: str,
    ):
        super().search_in_html_offer(downloaded_html_page)
        with open(downloaded_html_page, "r", encoding="utf-8") as file:
            html_content = file.read()

        # Extract contract type
        soup = BeautifulSoup(html_content, "html.parser")
        contract_tag = soup.find('span', class_='job-type job-info')
        if contract_tag:
            self.contract_type = contract_tag.get_text(strip=True)

    def get_expected_geopy_country_code(self) -> list[str | None]:
        return ["FR", None]

if __name__ == "__main__":
    import sys

    main_class = SanofiScrapper
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

