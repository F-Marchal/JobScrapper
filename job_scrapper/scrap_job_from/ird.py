from bs4 import BeautifulSoup
from typing import Iterator, Self

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk

class IRDScrapper(srk.JobScrapperSkeleton):
    """
    Use this file as a template to create your scrapper.
    """
    ##########################################################
    #  mandatory customisation of website dependant methods  #
    ##########################################################
    @classmethod
    def get_offer_listing_url(cls) -> str:
        return "https://emploi-recrutement.ird.fr/offre-de-emploi/liste-toutes-offres.aspx?page={page}"

    @classmethod
    def iter_trough_offer_listing(cls, url: str) -> Iterator["Self"]:
        return cls.get_web_processor().extract_block_across_multiple_pages_using_url(url)

    def get_expected_download_time(self) -> int:
        return -1

    @classmethod
    def find_offer_listing_on_page(cls, soup: BeautifulSoup) -> BeautifulSoup:
        return soup.find(
            name="div", class_="ts-related-offers__row text-center"
        )


    @classmethod
    def generate_offer_from_listing(cls, soup: BeautifulSoup) -> Iterator[Self]:
        # pylint: disable=R0914
        # Locals variables are here to simplify page parsing logic
        for cells in soup.find_all("div", class_="ts-offer-card Layer"):
            # title ref field
            title_ref_field = cells.find("a")["title"]

            title, ref_field = title_ref_field.split("(Réf. : ")
            split_ref_field = ref_field.split(" - ")
            field = split_ref_field[-1]
            ref = " - ".join(split_ref_field[:-1])

            # url
            url = cls.get_website_base_url() + str(cells.find("a")["href"])

            # Extract localisation and job type
            desc = cells.find("ul", class_="ts-offer-card-content__list")
            items = desc.find_all("li")
            team = items[0].get_text(strip=True)
            title = items[1].get_text(strip=True)
            localisation = items[2].get_text(strip=True)

            # pylint: disable=R0801
            # I do not see how to merge this part with other classes
            kwargs = {
                "field": None,
                "contract_type": None,
                "url": url,
                "localisation": localisation,
                "title": title,
                "reference": ref,
                "team": team,
            }
            yield cls(**kwargs)

    def search_in_html_offer(
            self,
            downloaded_html_page: str,
    ):
        super().search_in_html_offer(downloaded_html_page)
        with open(downloaded_html_page, "r", encoding="utf-8") as file:
            html_content = file.read()

        soup = BeautifulSoup(html_content, "html.parser")
        value = soup.find("p", id="fldoffer_customcodetablevalue2")
        if value:
            self.contract_type = value.get_text(strip=True)

    def get_expected_geopy_country_code(self) -> list[str | None]:
        return ["FR", None]

if __name__ == "__main__":
    import sys

    main_class = IRDScrapper
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
