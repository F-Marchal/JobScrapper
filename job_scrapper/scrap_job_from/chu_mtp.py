import re

from bs4 import BeautifulSoup

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk
from typing import Self, Iterator

class CHUMtpScrapper(srk.JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from CHUMtp's website
    """
    @classmethod
    def get_offer_listing_url(cls) -> str:
        """Returns a url that lead to an online listing of offers."""
        return "https://chu-montpellier.mstaff.co/offers?page={page}"

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
    def find_offer_listing_on_page(cls, soup) -> BeautifulSoup:
        return soup.find(
            name="div", class_="flex flex-col gap-y-6 grow max-w-[616px]"
        )

    @classmethod
    def generate_offer_from_listing(
        cls,
        soup,
    ) -> Iterator[Self]:
        for cells in soup.find_all("a"):
            title = re.findall(r'<span.*"offer_title">(.*)</span>', str(cells))[
                0
            ]

            contract_type, education_level, last_update = re.findall(
                r"<span>(.*)</span>", str(cells)
            )
            localisation = "Montpellier"
            url = str(cells["href"])

            # pylint: disable=R0801
            # I do not see how to merge this part with other classes
            kwargs = {
                "field": cls.try_to_find_field(title),
                "contract_type": contract_type,
                "url": url,
                "localisation": localisation,
                "title": title,
                "education_level": education_level,
                "last_update": last_update,
            }
            yield cls(**kwargs)

    def get_expected_geopy_country_code(self) -> list[str | None]:
        return ["FR"]

if __name__ == "__main__":
    main_class = CHUMtpScrapper

    import sys
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

    main_class.run(
        contact=f"{sys.argv[1]}-{main_class.get_standardised_class_name()}",
        keywords_to_search=keywords_to_search,
        page_exporter=main_class.get_page_exporter(),
    )