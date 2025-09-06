from bs4 import BeautifulSoup
import time

from selenium.common.exceptions import TimeoutException
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
        return soup.find(
            name="div",
            id="search-results-list"
        )

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
            field = str(cells.find("span", class_="job-category").get_text(strip=True)).replace(
                "Catégorie:", ""
            )

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
    def _rough_page_parsing_actions(cls, browser):
        super()._rough_page_parsing_actions(browser)
        # Wait for the button
        try:
            wait = WebDriverWait(browser, 5)
            btn = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.pagination-all a.pagination-show-all")
                )
            )
        except TimeoutException:
            # We assume that the button is not in this page (not enough offers)
            return

        # Find button
        browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
        time.sleep(cls.sleep_during_page_loading)

        #  Try to click the button
        wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "div.pagination-all a.pagination-show-all")
            )
        )
        btn.click()

        time.sleep(cls.sleep_during_page_loading)

class SanofiMontpellierScrapper(SanofiScrapper):
    website_url = "https://jobs.sanofi.com/fr/recherche-d%27offres/Montpellier%2C%20Occitanie/2649/4/3017382-11071623-3013500-2992165-6454034-2992166/43x61093/3x87635/50/2"

class SanofiClermontFDScrapper(SanofiScrapper):
    website_url = "https://jobs.sanofi.com/fr/recherche-d%27offres/Clermont-Ferrand%2C%20Auvergne-Rh%C3%B4ne-Alpes/2649/4/3017382-11071625-2984986-3024634-6440000-3024635/45x77969/3x08682/50/2"

class SanofiLyonScrapper(SanofiScrapper):
    website_url = "https://jobs.sanofi.com/fr/recherche-d%27offres/Lyon%2C%20Auvergne-Rh%C3%B4ne-Alpes/2649/4/3017382-11071625-2987410-2996943-6454573-2996944/45x74846/4x84671/50/2"

if __name__ == "__main__":
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

    result = SanofiLyonScrapper.interrogate_website()
    SanofiLyonScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"],
    )
    SanofiLyonScrapper.quick_display_list_of_offers(result)

