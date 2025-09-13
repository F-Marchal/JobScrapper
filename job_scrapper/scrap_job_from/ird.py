from bs4 import BeautifulSoup

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk


class IRDScrapper(srk.JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from IRD's website
    """

    website_url = "https://emploi-recrutement.ird.fr/offre-de-emploi/liste-toutes-offres.aspx?page={page}"
    job_across_multiple_pages = True

    @classmethod
    def extract_block_of_interest(cls, soup) -> BeautifulSoup:
        return soup.find(
            name="div", class_="ts-related-offers__row text-center"
        )

    @classmethod
    def complete_job_page_parsing(
        cls,
        offers: list["srk.ScrapperRequestCore"],
        soup,
    ):
        # pylint: disable=R0914
        # Locals variables are here to simplify page parsing logic
        for cells in soup.find_all("div", class_="ts-offer-card Layer"):
            # title ref field
            title_ref_field = cells.find("a")["title"]

            title, ref_field = title_ref_field.split("(Réf. : ")
            split_ref_field = ref_field.split(" - ")
            field = split_ref_field[-1]
            ref = " - ".join(split_ref_field[:-1])

            # url
            url = cls.get_base_url() + str(cells.find("a")["href"])

            # Extract localisation and job type
            desc = cells.find("ul", class_="ts-offer-card-content__list")
            items = desc.find_all("li")
            team = items[0].get_text(strip=True)
            title = items[1].get_text(strip=True)
            localisation = items[2].get_text(strip=True)

            # pylint: disable=R0801
            # I do not see how to merge this part with other classes
            kwargs = {
                "field": field,
                "contract_type": None,
                "url": url,
                "localisation": localisation,
                "title": title,
                "reference": ref,
                "team": team,
            }
            offers.append(cls(**kwargs))


if __name__ == "__main__":
    result = IRDScrapper.interrogate_website()
    IRDScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"],
    )
    IRDScrapper.quick_display_list_of_offers(result)
