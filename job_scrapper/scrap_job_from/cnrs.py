from bs4 import BeautifulSoup

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk
import time

class CNRScrapper(srk.JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from CNR's website
    """

    website_url = "https://emploi.cnrs.fr/RechercheAvancee.aspx"
    job_across_multiple_pages = False
    job_offer_fetch_require_manual_actions = True

    HEADERS = [
        "post_date",  # "Date de parution",
        "title",
        "localisation",  # "Type poste",
        "general_localisation",
        "contract_type",
    ]

    @classmethod
    def _job_offer_fetch_require_manual_actions_command(cls) -> list[BeautifulSoup]:
        i = 0
        continue_ = True
        pages = []
        while continue_:
            soup = cls._parse_region(i)
            i += 1

            if soup :
                pages.append(soup)
            else:
                continue_ = False

        return pages

    @classmethod
    def _parse_region(cls, index=0) -> BeautifulSoup | None:
        """CNRS' website contains a dropdown that show offers by regions.
        This function generate a BeautifulSoup soup for the item <index> in the dropdown.
        If the index iss too great, it returns None."""
        browser = cls.open_url_inside_browser(cls.website_url)
        time.sleep(cls.sleep_during_page_loading)

        dropdown_element = cls._wait_until_clickable(
            browser,
            (By.ID, "DdlBassinsGeographiques")
        )

        search_btn = cls._wait_until_clickable(
            browser,
            (By.ID, "CphMain_BtnRecherche")
        )

        dropdown = Select(dropdown_element)
        options = dropdown.options
        region_list = sorted([opt.get_attribute("value") for opt in options])
        if len(region_list) <= index:
            return None
        region = region_list[index]

        time.sleep(cls.sleep_during_page_loading)


        cls.logger.debug("Loading '%s'", region)
        dropdown.select_by_value(region)
        search_btn.click()

        time.sleep(cls.sleep_during_page_loading)
        cls._rough_page_parsing_actions(browser)

        html = browser.page_source
        browser.close()
        cls.logger.debug("Closing Chrome from %s (%s)", cls.website_url, region)

        soup = BeautifulSoup(html, "html.parser")
        return soup

    @classmethod
    def extract_block_of_interest(cls, soup) -> BeautifulSoup:
        return soup.find(
            name="tbody",
        )

    @classmethod
    def complete_job_page_parsing(
        cls,
        offers: list["srk.ScrapperRequestCore"],
        soup,
    ):
        for tr in soup.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]

            # Ignore empty cell
            if not cells:
                continue

            kwargs = dict(zip(cls.HEADERS, cells))

            # Find url
            url = cls.get_base_url() + str(tr.find("a")["href"])

            # Generate job
            offers.append(cls(field=None, url=url, **kwargs))

    def _search_keyword_in_page_content(
        self, page: BeautifulSoup | str, **keywords: list[str]
    ):
        if isinstance(page, BeautifulSoup):
            # Extract values contains inside "OffreDetailMainInfosGenerales".
            general_intel = page.find(
                name="div", class_="OffreDetailMainInfosGenerales"
            )

            if general_intel:
                for intel_pieces in general_intel.get_text().split("\n"):
                    metadata_name, *value = intel_pieces.split(":")

                    if not metadata_name.strip():
                        continue

                    self._metadata[metadata_name.strip()] = ":".join(
                        value
                    ).strip()

        return super()._search_keyword_in_page_content(page, **keywords)


if __name__ == "__main__":
    result = CNRScrapper.interrogate_website()
    CNRScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"],
    )
    CNRScrapper.quick_display_list_of_offers(result)
