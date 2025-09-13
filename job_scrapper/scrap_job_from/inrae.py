import re

from bs4 import BeautifulSoup

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk


class INRAEScrapper(srk.JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from INRAE's website
    """

    website_url = "https://jobs.inrae.fr/listingOffre?inrae_prod_created_date_desc[page]={page}"
    job_across_multiple_pages = True

    @classmethod
    def extract_block_of_interest(cls, soup) -> BeautifulSoup:
        return soup.find(name="div", id="infinite-hits")

    @classmethod
    def complete_job_page_parsing(
        cls,
        offers: list["srk.ScrapperRequestCore"],
        soup,
    ):
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
                "url": cls.get_base_url() + url,
                "localisation": localisation,
                "title": title,
            }
            offers.append(cls(**kwargs))


if __name__ == "__main__":
    result = INRAEScrapper.interrogate_website()
    INRAEScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"],
    )
    INRAEScrapper.quick_display_list_of_offers(result)
