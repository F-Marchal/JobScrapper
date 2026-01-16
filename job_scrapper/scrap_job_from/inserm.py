import re

from bs4 import BeautifulSoup
from typing import Iterator, Self

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk


class InsermScrapper(srk.JobScrapperSkeleton):
    """
    Use this file as a template to create your scrapper.
    """
    ##########################################################
    #  mandatory customisation of website dependant methods  #
    ##########################################################
    hide_web_driver = False

    @classmethod
    def get_offer_listing_url(cls) -> str:
        return "https://rh.inserm.fr/nous-rejoindre/Pages/Offres-d-emploi.aspx"

    @classmethod
    def iter_trough_offer_listing(cls, url: str) -> Iterator["Self"]:
        return cls.get_web_processor().extract_block_on_one_page(
            url,
            # prepare_page= # Not needed, offer are on the page
            # even when offer-button-container has not bee clicked
        )

    def get_expected_download_time(self) -> int:
        return 120

    @classmethod
    def find_offer_listing_on_page(cls, soup: BeautifulSoup) -> BeautifulSoup:
        return soup.find(name="div", class_="list-container")


    @classmethod
    def generate_offer_from_listing(cls, soup: BeautifulSoup) -> Iterator[Self]:
        for cells in soup.find_all("div", class_="offer-container"): # Access offer, even when hidden
            url = str(cells.find("a")["href"])
            title = re.findall(r'<a href=.*"_blank">(.*)</a>', str(cells))[0]
            post_date = cells.find("div", class_="publication-date").get_text(
                strip=True
            )
            localisation = cells.find("span", class_="location").get_text(
                strip=True
            )
            contract_type = cells.find("span", class_="contract-type").get_text(
                strip=True
            )
            education_level = cells.find("span", class_="details").get_text(
                strip=True
            )

            # pylint: disable=R0801
            # I do not see how to merge this part with other classes
            kwargs = {
                "field": None,
                "contract_type": contract_type,
                "url": url,
                "localisation": localisation,
                "title": title,
                "post_date": post_date,
                "education_level": education_level,
            }
            yield cls(**kwargs)


    def get_expected_geopy_country_code(self) -> list[str | None]:
        return  ["FR", None]

if __name__ == "__main__":
    import sys

    main_class = InsermScrapper
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