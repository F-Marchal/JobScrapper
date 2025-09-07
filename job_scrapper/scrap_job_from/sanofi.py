from bs4 import BeautifulSoup
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk


class SanofiScrapper(srk.JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from Sanofi's website
    """

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
            offers.append(SanofiScrapper(**kwargs))

    @classmethod
    def _rough_page_parsing_actions(cls, browser, timeout=15):
        super()._rough_page_parsing_actions(browser)
        try:
            wait = WebDriverWait(browser, timeout)

            # Wait until the button is present
            wait.until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "div.pagination-all a.pagination-show-all",
                    )
                )
            )

            # Wait until the button is clickable and then click
            button = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "div.pagination-all a.pagination-show-all",
                    )
                )
            )
            button.click()

            # Optional wait for page to load
            WebDriverWait(browser, timeout).until(
                EC.staleness_of(button)  # waits until button becomes stale
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
        ):
            # Retry once if button became stale or was intercepted
            try:
                button = browser.find_element(
                    By.CSS_SELECTOR, "div.pagination-all a.pagination-show-all"
                )
                button.click()
            except WebDriverException as wbe:
                cls.logger.warning(
                    "Can not click on the 'Show all' button. Some offers might be ignored. %s",
                    wbe,
                )
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
    result = SanofiLyonScrapper.interrogate_website()
    SanofiLyonScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"],
    )
    SanofiLyonScrapper.quick_display_list_of_offers(result)

    result = SanofiMontpellierScrapper.interrogate_website()
    SanofiMontpellierScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"],
    )
    SanofiMontpellierScrapper.quick_display_list_of_offers(result)

    result = SanofiClermontFDScrapper.interrogate_website()
    SanofiClermontFDScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"],
    )
    SanofiClermontFDScrapper.quick_display_list_of_offers(result)
