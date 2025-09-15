import time
from typing import Callable

from bs4 import BeautifulSoup
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk


class SanofiScrapper(srk.JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from Sanofi's website (Limited to France)
    """
    website_url = "https://jobs.sanofi.com/fr/recherche-d%27offres/France/2649/2/3017382/46/2/50/2"
    job_across_multiple_pages = False

    @classmethod
    def extract_block_of_interest(cls, soup) -> BeautifulSoup:
        return soup.find(name="div", id="search-results-list")

    @classmethod
    def complete_job_page_parsing(
        cls,
        offers: list["srk.ScrapperRequestCore"],
        soup,
    ):
        for cells in soup.find_all("li"):
            url = cls.get_base_url() + str(cells.find("a")["href"])
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
            offers.append(cls(**kwargs))

    @classmethod
    def interrogate_website(
        cls, prepare_page: Callable | None = None
    ) -> list[srk.ScrapperRequestCore]:
        if prepare_page is None:
            prepare_page = cls._job_rough_page_parsing_actions
        return super().interrogate_website(prepare_page)

    @classmethod
    def _rough_page_parsing_actions(cls, browser) -> None:
        try:
            cookie_btn = WebDriverWait(browser, 3).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "button.onetrust-close-btn-handler.banner-close-button.ot-close-link",
                    )
                )
            )
            cookie_btn.click()
            cls.logger.debug("Cookies pop up is closed.")
        except TimeoutException:
            cls.logger.debug("No cookies pop up found.")

        super()._rough_page_parsing_actions(browser)

    @classmethod
    def _job_rough_page_parsing_actions(cls, browser, timeout=15):
        """
        A method called each time a page that contains a list of jobs should be parsed.
        :param browser: A selenium browser
        :param int timeout: How long can the browser wait (s).
        """
        cls._rough_page_parsing_actions(browser)
        button_id = (
            "div.pagination-all a.pagination-show-all"  # pagination-show-all
        )
        try:
            wait = WebDriverWait(browser, timeout)

            # wait until the button is clickable
            button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, button_id))
            )

            # Execute button's script (as if we clicked on it)
            browser.execute_script("arguments[0].click();", button)

            # wait for update
            wait.until(
                EC.staleness_of(button)  # ou une autre condition adaptée
            )

        except TimeoutException:
            # Button not found – probably no "show all" option
            cls.logger.debug(
                "'Show all' button not found. Assume that all jobs are already in display'"
            )
            return
        except (
            StaleElementReferenceException,
            ElementClickInterceptedException,
        ) as wbe:

            cls.logger.warning(
                "Can not click on the 'Show all' button. Some offers might be ignored. %s",
                wbe,
            )
            time.sleep(50)
            return


class SanofiMontpellierScrapper(SanofiScrapper):
    """
    Use JobScrapperSkeleton to extract jobs offers located in Montpellier from Sanofi's website
    """

    website_url = "https://jobs.sanofi.com/fr/recherche-d%27offres/Montpellier%2C%20Occitanie/2649/4/3017382-11071623-3013500-2992165-6454034-2992166/43x61093/3x87635/50/2"


class SanofiClermontFDScrapper(SanofiScrapper):
    """
    Use JobScrapperSkeleton to extract jobs offers located in Clermont-Ferrand from Sanofi's website
    """

    website_url = "https://jobs.sanofi.com/fr/recherche-d%27offres/Clermont-Ferrand%2C%20Auvergne-Rh%C3%B4ne-Alpes/2649/4/3017382-11071625-2984986-3024634-6440000-3024635/45x77969/3x08682/50/2"


class SanofiLyonScrapper(SanofiScrapper):
    """
    Use JobScrapperSkeleton to extract jobs offers located in Lyon from Sanofi's website
    """

    website_url = "https://jobs.sanofi.com/fr/recherche-d%27offres/Lyon%2C%20Auvergne-Rh%C3%B4ne-Alpes/2649/4/3017382-11071625-2987410-2996943-6454573-2996944/45x74846/4x84671/50/2"


if __name__ == "__main__":
    result = SanofiScrapper.interrogate_website()
    SanofiScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"],
    )
    SanofiScrapper.quick_display_list_of_offers(result)
