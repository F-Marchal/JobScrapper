from bs4 import BeautifulSoup
import re
from job_scrapper.scrapper_skeleton import JobScrapperSkeleton


class CHUMtpScrapper(JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from CHUMtp's website
    """
    website_url = "https://chu-montpellier.mstaff.co/offers?page={page}"
    across_multiple_pages = True

    @classmethod
    def extract_block_of_interest(cls, soup) -> BeautifulSoup:
        return soup.find(name="div", class_="flex flex-col gap-y-6 grow max-w-[616px]")

    @classmethod
    def complete_job_page_parsing(
        cls,
        offers: list["JobScrapperSkeleton"],
        soup,
    ):
        # pylint: disable=R0914
        # Locals variables are here to simplify page parsing logic
        for cells in soup.find_all(
            "a",
        ):
            title = re.findall(r'<span.*"offer_title">(.*)</span>', str(cells))[0]

            contract_type, education_level, last_update = re.findall(
                r"<span>(.*)</span>", str(cells)
            )
            localisation = "Montpellier"
            url = str(cells["href"])

            kwargs = {
                "field": None,
                "contract_type": contract_type,
                "url": url,
                "localisation": localisation,
                "title": title,
                "education_level": education_level,
                "last_update": last_update,
            }
            offers.append(CHUMtpScrapper(**kwargs))

if __name__ == "__main__":
    result = CHUMtpScrapper.interrogate_website()
    CHUMtpScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"]
    )
    CHUMtpScrapper.quick_display_list_of_offers(result)
