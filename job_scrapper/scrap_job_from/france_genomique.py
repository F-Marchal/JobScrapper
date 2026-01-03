from bs4 import BeautifulSoup
from typing import Iterator, Self

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk
import re

class FranceGenomiqueScrapper(srk.JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from FranceGenomique's website
    """
    ##########################################################
    #  mandatory customisation of website dependant methods  #
    ##########################################################
    @classmethod
    def get_offer_listing_url(cls) -> str:
        return "https://www.france-genomique.org/recrutement-offres-emploi/"

    @classmethod
    def iter_trough_offer_listing(cls, url: str) -> Iterator["Self"]:
        return cls.get_web_processor().extract_block_on_one_page(url)

    def get_expected_download_time(self) -> int:
        return -1

    @classmethod
    def find_offer_listing_on_page(cls, soup: BeautifulSoup) -> BeautifulSoup:
        return soup.find(
            name="div",
            class_="row single-top-padding single-bottom-padding single-h-padding limit-width row-parent",
        )



    @classmethod
    def generate_offer_from_listing(cls, soup: BeautifulSoup) -> Iterator[Self]:
        # pylint: disable=R0914
        # Locals variables are here to simplify page parsing logic

        for cells in soup.find_all(  # pylint: disable=W0612
                "div", class_="t-entry"
        ):
            str_cell = str(cells)
            tmp_contract = cells.find(
                "a", class_="style-accent-bg tmb-term-evidence font-ui"
            )
            if tmp_contract:
                contract_type = tmp_contract.get_text(strip=True)
            else:
                contract_type = None

            tmp_title_localisation = cells.find(
                "h2", class_="t-entry-title h6 title-scale"
            ).get_text(strip=True)
            title, localisation = tmp_title_localisation.split("(")
            localisation = localisation.removesuffix(")")
            url = re.findall('<a class="btn btn-link" href="(.*)" ', str_cell)[
                0
            ]

            kwargs = {
                "field": cls.try_to_find_field(title),
                "contract_type": contract_type,
                "url": url,
                "localisation": localisation,
                "title": title,
            }
            yield cls(**kwargs)

    def get_expected_geopy_country_code(self) -> list[str | None]:
        return ["FR", None]

if __name__ == "__main__":
    import sys

    main_class = FranceGenomiqueScrapper
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
