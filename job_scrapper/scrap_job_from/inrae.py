import re

from bs4 import BeautifulSoup
from typing import Iterator, Self

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk


class INRAEScrapper(srk.JobScrapperSkeleton):
    """
    Use this file as a template to create your scrapper.
    """
    ##########################################################
    #  mandatory customisation of website dependant methods  #
    ##########################################################
    @classmethod
    def get_offer_listing_url(cls) -> str:
        return "https://jobs.inrae.fr/listingOffre?inrae_prod_created_date_desc[page]={page}"

    @classmethod
    def iter_trough_offer_listing(cls, url: str) -> Iterator["Self"]:
        return cls.get_web_processor().extract_block_across_multiple_pages_using_url(url)

    def get_expected_download_time(self) -> int:
        return -1

    @classmethod
    def find_offer_listing_on_page(cls, soup: BeautifulSoup) -> BeautifulSoup:
        return soup.find(name="div", id="infinite-hits")


    @classmethod
    def generate_offer_from_listing(cls, soup: BeautifulSoup) -> Iterator[Self]:
        for cells in soup.find_all("a", class_="Cardjob"):
            title = re.findall(r"<span>(.*)</span>", str(cells))[0]
            localisation = cells.find(
                "div", class_="Cardjob-location"
            ).text.strip()

            # contract_type
            contract_type = cells.find(
                "span", class_=re.compile(r"^Cardjob-contract")
            ).text.strip()

            url = cells["href"]

            kwargs = {
                "field": None,
                "contract_type": contract_type,
                "url": cls.get_website_base_url() + url,
                "localisation": localisation,
                "title": title,
            }
            yield cls(**kwargs, overwrite_job_entry={"title"})

    def get_expected_geopy_country_code(self) -> list[str | None]:
        return ["FR", None]

    def search_in_html_offer(
            self,
            downloaded_html_page: str,
    ):
        super().search_in_html_offer(downloaded_html_page)
        with open(downloaded_html_page, "r", encoding="utf-8") as file:
            html_content = file.read()

        soup = BeautifulSoup(html_content, "html.parser")
        title_tag = soup.find("h1", class_="Hero-title")
        if title_tag:
            self.title = title_tag.get_text(strip=True)

if __name__ == "__main__":
    import sys

    main_class = INRAEScrapper
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
