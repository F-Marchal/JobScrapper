import sys

from bs4 import BeautifulSoup
from typing import Iterator, Self

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk
from sql.tables.helpers.keyword_manager import KeywordManager
from web_processing.block_extractor import WebBlockExtractor


class CiradScrapper(srk.JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from Cirad's website
    """
    ##########################################################
    #  mandatory customisation of website dependant methods  #
    ##########################################################
    @classmethod
    def get_offer_listing_url(cls) -> str:
        """Returns a url that lead to an online listing of offers."""
        return "https://recrutement.cirad.fr/offre-de-emploi/liste-toutes-offres.aspx?page={page}"

    @classmethod
    def iter_trough_offer_listing(cls, url: str) -> Iterator["Self"]:
        """Iter through each pages of the online listing <get_offer_listing_url>.
              If you need to (re)write this method the simplest method are :

              When only one page is expected:
                  - `cls.get_web_processor().extract_block_on_one_page(url)`

              When the url contains the page number :
                  - `cls.get_web_processor().extract_block_across_multiple_pages_using_url(url)`

              When the url does not contain the page number:
                  - `cls.get_web_processor().extract_block_across_multiple_pages_using_buttons(
                      url,
                      button_finder
                  )`
        """
        return cls.get_web_processor().extract_block_across_multiple_pages_using_url(
            url
        )

    def get_expected_download_time(self) -> int:
        """If offers on the scrapped website are contained inside files
        (pdf ...), the file should be downloaded.
        This function says how long the download is expected to take.
        Returns -1 if no download (file) is expected."""
        return -1

    @classmethod
    def find_offer_listing_on_page(cls, soup: BeautifulSoup) -> BeautifulSoup:
        """Should return a BeautifulSoup that only contains the offer listing.
        (This soup should not contain webpage header / footer other metadata.)"""
        return soup.find(name="div", class_="ts-related-offers listing-offres")

    @classmethod
    def generate_offer_from_listing(cls, soup: BeautifulSoup) -> Iterator[Self]:
        """Generate a number of scrapper object from a block of HTML code that
        should correspond to the listing of offers."""
        # pylint: disable=R0914
        # Locals variables are here to simplify page parsing logic

        for cells in soup.find_all(
            "li", class_="ts-offer-list-item offerlist-item"
        ):
            # Extract title, ref and field
            title_ref_field = cells.find("a")["title"]
            *title_ref_elements, field = title_ref_field.split(" - ")
            title_ref = "_".join(title_ref_elements)
            title, ref = title_ref.split("(Réf. :")
            ref = ref[:-1].strip()

            # Extract localisation and job type
            desc = cells.find("ul", class_="ts-offer-list-item__description")
            items = desc.find_all("li")
            post_date = items[1].get_text(strip=True)
            contract_type = items[2].get_text(strip=True)
            localisation = items[3].get_text(strip=True)

            # Extract url
            url = cls.get_website_base_url() + str(cells.find("a")["href"])

            kwargs = {
                "field": field,
                "contract_type": contract_type,
                "url": url,
                "localisation": localisation,
                "title": title,
                "reference": ref,
                "post date": post_date,
            }

            yield cls(**kwargs)

    def get_expected_geopy_country_code(self) -> list[str | None]:
        return ["FR", None]

if __name__ == "__main__":
    main_class = CiradScrapper
    if len(sys.argv) < 2:
        raise IndexError(
            "This script expect one argument : Contact information.\n\n"
            "Please run this program (python 3 <file> <contact>) using your\n"
            "email as contact. This is mandatory to comply with Geopy terms\n"
            "of services. Your <contact> information will be transmitted to\n"
            "geopy and might be written inside (local) log file / terminal. "
            ""
        )

    import sys
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