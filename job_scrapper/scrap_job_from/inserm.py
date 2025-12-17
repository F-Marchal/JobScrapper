import re

from bs4 import BeautifulSoup

import job_scrapper.scrapper_skeleton.pdf_jobs as pj
from job_scrapper.scrapper_skeleton.legacy_request_core import ScrapperRequestCore


class InsermScrapper(pj.PdfJobBaseScrapper):
    """
    Use JobScrapperSkeleton to extract jobs offers from Inserm's website
    """

    website_url = (
        "https://rh.inserm.fr/nous-rejoindre/Pages/Offres-d-emploi.aspx"
    )
    job_across_multiple_pages = False

    @classmethod
    def extract_block_of_interest(cls, soup) -> BeautifulSoup:
        return soup.find(name="div", class_="list-container")

    @classmethod
    def complete_job_page_parsing(
        cls,
        offers: list[ScrapperRequestCore],
        soup,
    ):
        for cells in soup.find_all("div", class_="offer-container"):
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
            offers.append(cls(**kwargs))


if __name__ == "__main__":
    result = InsermScrapper.interrogate_website()
    InsermScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"],
    )
    InsermScrapper.quick_display_list_of_offers(result)
