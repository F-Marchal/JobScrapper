from bs4 import BeautifulSoup
from typing import Iterator, Self

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk
from job_scrapper.web_processing.enhanced_chrome_browser import EnhancedChrome
from selenium.webdriver.common.by import By

class IfremerScrapper(srk.JobScrapperSkeleton):
    """
    Use this file as a template to create your scrapper.
    """

    @classmethod
    def get_offer_listing_url(cls) -> str:
        return "https://www.hellowork.com/fr-fr/entreprises/ifremer-9336.html?p={page}"

    @classmethod
    def iter_trough_offer_listing(cls, url: str) -> Iterator["Self"]:
        return cls.get_web_processor().extract_block_across_multiple_pages_using_url(
            url,
            prepare_page=cls.close_popups
        )

    @classmethod
    def close_popups(cls, driver: "EnhancedChrome"):
        driver.safe_close_pop_up(
            selector=By.ID,
            button_id="hw-cc-notice-continue-without-accepting-btn",
        )
        # Google popup
        # driver.safe_close_pop_up(
        #     selector=By.CSS_SELECTOR,
        #     button_id='svg[data-cross-origin-svg-url-value*="close.svg"]',
        # )
        driver.scroll_to_bottom()


    def get_expected_download_time(self) -> int:
        return -1

    @classmethod
    def find_offer_listing_on_page(cls, soup: BeautifulSoup) -> BeautifulSoup:
        return soup.find(name="turbo-frame", id="offersListFrame")


    @classmethod
    def generate_offer_from_listing(cls, soup: BeautifulSoup) -> Iterator[Self]:
        # pylint: disable=R0914
        # Locals variables are here to simplify page parsing logic
        if not soup:
            return

        for cells in soup.find_all(  # pylint: disable=W0612
            "div",
            class_="tw-flex tw-flex-col tw-justify-between tw-size-full tw-p-4 sm:tw-p-6 sm:small-group:tw-p-4",
        ):
            tmp_title_url = cells.find(
                "a",
                class_="tw-no-underline tw-outline-none focus-within:tw-underline tw-forwarder tw-inline",
            )
            url = cls.get_website_base_url() + str(tmp_title_url["href"])
            title = tmp_title_url.get_text(strip=True)

            tmp_localisation = cells.find(
                "div",
                {
                    "class": [
                        "tw-readonly",
                        "tw-tag-secondary-s",
                        "tw-w-fit",
                        "tw-border-0",
                    ],
                    "data-cy": "localisationCard",
                },
            )
            tmp_contract = cells.find(
                "div",
                {
                    "class": [
                        "tw-readonly",
                        "tw-tag-secondary-s",
                        "tw-w-fit",
                        "tw-border-0",
                    ],
                    "data-cy": "contractCard",
                },
            )
            tmp_contract_tag = cells.find_all(
                "div",
                {
                    "class": [
                        "tw-readonly",
                        "tw-tag-secondary-s",
                        "tw-border-0",
                        "tw-w-fit",
                    ],
                    "data-cy": "contractTag",
                },
            )
            tmp_post_date = cells.find(
                "div", class_="w-typo-s tw-text-grey-500 tw-pl-1 tw-pt-1"
            )

            localisation = (
                tmp_localisation.get_text(strip=True)
                if tmp_localisation
                else None
            )
            if isinstance(localisation, str) and " - " in localisation:
                split_loc = localisation.split(" - ")
                localisation = split_loc[0]

            contract = (
                tmp_contract.get_text(strip=True) if tmp_contract else None
            )
            post_date = (
                tmp_post_date.get_text(strip=True) if tmp_post_date else None
            )

            contract_tag_list = (
                [tag.get_text(strip=True) for tag in tmp_contract_tag]
                if tmp_contract_tag
                else []
            )
            contract_tag = ";".join(
                [str(tag) for tag in contract_tag_list if tag]
            )

            kwargs = {
                "field": None,
                "contract_type": contract,
                "url": url,
                "localisation": localisation,
                "title": title,
                "contract_tag": contract_tag,
            }

            if post_date:
                kwargs["post_date"] = post_date

            yield cls(**kwargs)

    def get_expected_geopy_country_code(self) -> list[str | None]:
        """Returns a list of country code that can help geopy / Nominatim
        to figure the right coordinate of self.localisation.
        You can use ISO 3166-1 alpha-2 country codes
        (https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2#Officially_assigned_code_elements)

        Geopy will only search inside country code that are listed here. You can use
        `None` in the returned list to search without geographic restrictions.

        return ["FR", None] --> Search in France then all around the world
        return ["FR", "UM"] --> Search in France then United States
        return ["FR", "UM", None] --> Search in France then United States then  all around the world
        """
        return ["FR", None]

if __name__ == "__main__":
    import sys

    main_class = IfremerScrapper
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

