import re
import time

import bs4
from bs4 import BeautifulSoup

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk
from typing import Generator
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class SFBIScrapper(srk.JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from SBI's website
    """

    website_url = "https://www.sfbi.fr/emplois/offres-en-cours"
    job_across_multiple_pages = True
    job_across_multiple_pages_mandatory_action = True
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

    @classmethod
    def extract_block_of_interest(cls, soup) -> list[BeautifulSoup]:
        return soup.find(
            name="table",
        )

    @classmethod
    def _job_across_multiple_pages_command_action(cls) -> list[bs4.BeautifulSoup]:
        browser = cls.open_url_inside_browser(cls.website_url)
        is_disabled = False
        all_pages = []
        i = 1
        while not is_disabled:
            cls._rough_page_parsing_actions(browser)
            if i == 1:
                cls.logger.debug("Loading page %s", i)
                html = browser.page_source
                soup = BeautifulSoup(html, "html.parser")
                all_pages.append(soup)
            i += 1

            next_page_btn = WebDriverWait(browser, 5).until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            "button.page-link.next",
                        )
                    )
                )
            is_disabled = next_page_btn.get_attribute("aria-disabled")

            if not is_disabled:
                next_page_btn.click()
                cls.logger.debug("Loading page %s", i)
                html = browser.page_source
                soup = BeautifulSoup(html, "html.parser")
                all_pages.append(soup)
                time.sleep(cls.sleep_during_page_loading)


            else:
                cls.logger.debug("No page %s, closing browser on %s", i + 1, cls.website_url)
                browser.close()

        return all_pages

    @classmethod
    def complete_job_page_parsing(
        cls,
        offers: list["srk.ScrapperRequestCore"],
        soup,
    ):
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
            url = cls.get_base_url() + re_url[0]

            # Generate job
            offers.append(cls(field="Bioinformatic", url=url, **kwargs))


if __name__ == "__main__":
    result = SFBIScrapper.interrogate_website()
    SFBIScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"],
    )
    SFBIScrapper.quick_display_list_of_offers(result)
