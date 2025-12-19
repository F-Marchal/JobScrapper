import sys

from bs4 import BeautifulSoup
from typing import Iterator, Self

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk
from sql.tables.helpers.keyword_manager import KeywordManager
from web_processing.block_extractor import WebBlockExtractor
from web_processing.enhanced_chrome_browser import ButtonFinder

class TemplateScrapper(srk.JobScrapperSkeleton):
    """
    Use this file as a template to create your scrapper.
    """
    ##########################################################
    #  mandatory customisation of website dependant methods  #
    ##########################################################
    @classmethod
    def get_offer_listing_url(cls) -> str:
        """Returns a url that lead to an online listing of offers.
        You can use {page} in the url if the offers are split
        trough multiple pages and page number is in the url.
            https://websire.com/{page}
        """
        raise NotImplementedError

    @classmethod
    def iter_trough_offer_listing(cls, url: str) -> Iterator["Self"]:
        """
        Iter through each pages of the online listing <get_offer_listing_url>.
              If you need to (re)write this method the simplest method are :

              When only one page is expected:
                  - `cls.get_web_processor().extract_block_on_one_page(url)`

              When the url contains the page number :
                  - `cls.get_web_processor().extract_block_across_multiple_pages_using_url(url)`

              When the url does not contain the page number:
                  - ```cls.get_web_processor().extract_block_across_multiple_pages_using_buttons(
                      url,
                      button_finder
                  )```
                  You might need to create an additional method to use as button_finder.
                  This method should match a `ButtonFinder`. See ButtonFinder Docs.
        """
        raise NotImplementedError

    def get_expected_download_time(self) -> int:
        """
        If offers on the scrapped website are contained inside files
        (pdf ...), the file should be downloaded.
        This function says how long the download is expected to take.
        Returns -1 if no download (file) is expected.
        """
        raise NotImplementedError

    @classmethod
    def find_offer_listing_on_page(cls, soup: BeautifulSoup) -> BeautifulSoup:
        """Should return a BeautifulSoup that only contains the offer listing.
        (This soup should not contain webpage header / footer other metadata.)

        You can use ctrl + maj + c on your navigator to inspect HTML code and find
        the block of code that contain the listing.

        As an example on https://recrutement.cirad.fr/accueil.aspx?LCID=103
        the container is defined by  <div id="main" class="ts-related-offers listing-offres">
        and the function can be :
        return soup.find(name="div", class_="ts-related-offers listing-offres")
        """
        raise NotImplementedError


    @classmethod
    def generate_offer_from_listing(cls, soup: BeautifulSoup) -> Iterator[Self]:
        """Generate a number of scrapper object from a block of HTML code that
        should correspond to the listing of offers.

        You can use ctrl + maj + c on your navigator to inspect HTML code and find
        the code that define each offer container.

        As an example on https://recrutement.cirad.fr/accueil.aspx?LCID=103
        each container is defined by  <li class="ts-offer-list-item offerlist-item " title="" onclick=...>
        and the loop can be
        ```
        for cells in soup.find_all(
            "li", class_="ts-offer-list-item offerlist-item"
        ):
            # Extract as much information as possible :
            information = {}
            information['title'] = cells.find("a")["title"]
            # ...
            yield cls(**information)

            # Do not forget that you can complete offers information
            # By parsing offer content rewriting :
            # def search_in_html_offer(self,  downloaded_html_page: str)
            # or
            # def search_in_text_offer(self,  downloaded_text_page: str)
        ```

        It is expected that each cell contains one offer and lead to the creation
        of a new instance of cls.
        """
        raise NotImplementedError

if __name__ == "__main__":
    import sys

    main_class = TemplateScrapper
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