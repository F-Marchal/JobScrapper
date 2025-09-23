from bs4 import BeautifulSoup

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import time
class IfremerScrapper(srk.JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from Ifremer's website
    """

    website_url = "https://www.hellowork.com/fr-fr/entreprises/ifremer-9336.html?p={page}"
    job_across_multiple_pages = True
    job_offer_fetch_require_manual_actions = False
    @classmethod
    def _rough_page_parsing_actions(cls, browser) -> None:
        cls._close_pop_up(
            browser=browser,
            by=By.ID,
            button_identifier="hw-cc-notice-continue-without-accepting-btn",
            msg="Cookies pop up"
        )
        cls._close_pop_up(
            browser=browser,
            by=By.CSS_SELECTOR,
            button_identifier='svg[data-cross-origin-svg-url-value*="close.svg"]',
            msg="Google connexion pop up"
        )
        super()._rough_page_parsing_actions(browser)


    @classmethod
    def extract_block_of_interest(cls, soup) -> BeautifulSoup:
        tmp = soup.find(
            name="turbo-frame",
            id="offersListFrame"
        )
        return tmp

    @classmethod
    def complete_job_page_parsing(
        cls,
        offers: list["srk.ScrapperRequestCore"],
        soup,
    ):
        # pylint: disable=R0914
        # Locals variables are here to simplify page parsing logic
        for cells in soup.find_all( # pylint: disable=W0612
            "div", class_="tw-flex tw-flex-col tw-justify-between tw-size-full tw-p-4 sm:tw-p-6 sm:small-group:tw-p-4"
        ):
            tmp_title_url = cells.find(
                "a",
                class_="tw-no-underline tw-outline-none focus-within:tw-underline tw-forwarder tw-inline"
                )
            url = cls.get_base_url() + str(tmp_title_url["href"])
            title = tmp_title_url.get_text(strip=True)

            tmp_localisation = cells.find("div", {
                    "class": ["tw-readonly", "tw-tag-secondary-s", "tw-w-fit", "tw-border-0"],
                    "data-cy": "localisationCard"
                })
            tmp_contract = cells.find("div", {
                    "class": ["tw-readonly", "tw-tag-secondary-s", "tw-w-fit", "tw-border-0"],
                    "data-cy": "contractCard"
                })
            tmp_contract_tag = cells.find_all("div", {
                    "class": ["tw-readonly", "tw-tag-secondary-s", "tw-border-0", "tw-w-fit"],
                    "data-cy": "contractTag"
                })
            tmp_post_date = cells.find("div", class_="w-typo-s tw-text-grey-500 tw-pl-1 tw-pt-1")


            localisation = tmp_localisation.get_text(strip=True) if tmp_localisation else None
            contract = tmp_contract.get_text(strip=True) if tmp_contract else None
            post_date = tmp_post_date.get_text(strip=True) if tmp_post_date else None

            contract_tag_list = [tag.get_text(strip=True) for tag in tmp_contract_tag] if tmp_contract_tag else []
            contract_tag = ";".join([str(tag) for tag in contract_tag_list if tag])

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
            offers.append(cls(**kwargs))


if __name__ == "__main__":
    result = IfremerScrapper.interrogate_website()
    IfremerScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"],
    )
    IfremerScrapper.quick_display_list_of_offers(result)
