from bs4 import BeautifulSoup
import re
import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk


class TemplateScrapper(srk.JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from Template's website
    """

    website_url = "-"
    job_across_multiple_pages = True
    HEADERS = [
        "title",  # "Titre",
        "Niveau",
        "contract_type",  # "Type poste",
        "Contrat",
        "Durée",
        "Equipe",
        "localisation",  # "Lieu",
        "beginning",  # "Date début",
        "end",  # "Date fin",
        "Référence",
    ]

    @classmethod
    def extract_block_of_interest(cls, soup) -> BeautifulSoup:
        return soup.find(
            name="table",
        )



    @classmethod
    def complete_job_page_parsing(
        cls,
        offers: list["srk.ScrapperRequestCore"],
        soup,
    ):
        for tr in soup.find_all("tr"):
            # "tr" keyword indicate a table
            # "td" keyword indicate the end of a cell
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            kwargs = dict(zip(cls.HEADERS, cells))

            # Ignore empty cell
            if not cells:
                continue

            # Find url
            re_url = re.findall('<td><a href="(.*)"', str(tr))
            url = cls.get_base_url() + re_url[0]

            # Generate job
            offers.append(cls(field="Bioinformatic", url=url, **kwargs))


if __name__ == "__main__":
    result = TemplateScrapper.interrogate_website()
    TemplateScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"],
    )
    TemplateScrapper.quick_display_list_of_offers(result)
