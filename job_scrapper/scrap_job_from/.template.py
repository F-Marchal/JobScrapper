from bs4 import BeautifulSoup

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk


class TemplateScrapper(srk.JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from Template's website
    """

    website_url = "-"
    job_across_multiple_pages = True

    @classmethod
    def extract_block_of_interest(cls, soup) -> BeautifulSoup:
        return soup.find(
            name="-",
            class_="-"
        )

    @classmethod
    def complete_job_page_parsing(
        cls,
        offers: list["srk.ScrapperRequestCore"],
        soup,
    ):
        # pylint: disable=R0914
        # Locals variables are here to simplify page parsing logic

        for cells in soup.find_all( # pylint: disable=W0612
            "-", class_="-"
        ):
            continue


if __name__ == "__main__":
    result = TemplateScrapper.interrogate_website()
    TemplateScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"],
    )
    TemplateScrapper.quick_display_list_of_offers(result)
