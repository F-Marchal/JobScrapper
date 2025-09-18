from bs4 import BeautifulSoup

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk


class CNRScrapper(srk.JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from CNR's website
    """

    website_url = "https://emploi.cnrs.fr/RechercheAvancee.aspx"
    job_across_multiple_pages = False
    HEADERS = [
        "post_date",  # "Date de parution",
        "title",
        "localisation",  # "Type poste",
        "general_localisation",
        "contract_type",
    ]

    @classmethod
    def extract_block_of_interest(cls, soup) -> BeautifulSoup:
        return soup.find(
            name="tbody",
        )

    @classmethod
    def complete_job_page_parsing(
        cls,
        offers: list["srk.ScrapperRequestCore"],
        soup,
    ):
        for tr in soup.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]

            # Ignore empty cell
            if not cells:
                continue

            kwargs = dict(zip(cls.HEADERS, cells))

            # Find url
            url = cls.get_base_url() + str(tr.find("a")["href"])

            # Generate job
            offers.append(cls(field=None, url=url, **kwargs))

    def _search_keyword_in_page_content(
        self, page: BeautifulSoup | str, **keywords: list[str]
    ):
        if isinstance(page, BeautifulSoup):
            # Extract values contains inside "OffreDetailMainInfosGenerales".
            general_intel = page.find(
                name="div", class_="OffreDetailMainInfosGenerales"
            )

            if general_intel:
                for intel_pieces in general_intel.get_text().split("\n"):
                    metadata_name, *value = intel_pieces.split(":")

                    if not metadata_name.strip():
                        continue

                    self._metadata[metadata_name.strip()] = ":".join(
                        value
                    ).strip()

        return super()._search_keyword_in_page_content(page, **keywords)


if __name__ == "__main__":
    result = CNRScrapper.interrogate_website()
    CNRScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"],
    )
    CNRScrapper.quick_display_list_of_offers(result)
