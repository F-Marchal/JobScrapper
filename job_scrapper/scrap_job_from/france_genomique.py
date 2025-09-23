import re

from bs4 import BeautifulSoup

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk


class FranceGenomiqueScrapper(srk.JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from FranceGenomique's website
    """

    website_url = "https://www.france-genomique.org/recrutement-offres-emploi/"
    job_across_multiple_pages = False

    @classmethod
    def extract_block_of_interest(cls, soup) -> BeautifulSoup:
        return soup.find(
            name="div",
            class_="row single-top-padding single-bottom-padding single-h-padding limit-width row-parent",
        )

    @classmethod
    def complete_job_page_parsing(
        cls,
        offers: list["srk.ScrapperRequestCore"],
        soup,
    ):
        # pylint: disable=R0914
        # Locals variables are here to simplify page parsing logic

        for cells in soup.find_all(  # pylint: disable=W0612
            "div", class_="t-entry"
        ):
            str_cell = str(cells)
            tmp_contract = cells.find(
                "a", class_="style-accent-bg tmb-term-evidence font-ui"
            )
            if tmp_contract:
                contract_type = tmp_contract.get_text(strip=True)
            else:
                contract_type = None

            tmp_title_localisation = cells.find(
                "h2", class_="t-entry-title h6 title-scale"
            ).get_text(strip=True)
            title, localisation = tmp_title_localisation.split("(")
            localisation = localisation.removesuffix(")")
            url = re.findall('<a class="btn btn-link" href="(.*)" ', str_cell)[
                0
            ]

            kwargs = {
                "field": None,
                "contract_type": contract_type,
                "url": url,
                "localisation": localisation,
                "title": title,
            }
            offers.append(cls(**kwargs))


if __name__ == "__main__":
    result = FranceGenomiqueScrapper.interrogate_website()
    FranceGenomiqueScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"],
    )
    FranceGenomiqueScrapper.quick_display_list_of_offers(result)
