from bs4 import BeautifulSoup

import job_scrapper.scrapper_skeleton.scrapper_skeleton as srk


class CiradScrapper(srk.JobScrapperSkeleton):
    """
    Use JobScrapperSkeleton to extract jobs offers from Cirad's website
    """

    website_url = "https://recrutement.cirad.fr/offre-de-emploi/liste-toutes-offres.aspx?page={page}"
    across_multiple_pages = True

    @classmethod
    def extract_block_of_interest(cls, soup) -> BeautifulSoup:
        return soup.find(name="div", class_="ts-related-offers listing-offres")

    @classmethod
    def complete_job_page_parsing(
        cls,
        offers: list["srk.ScrapperRequestCore"],
        soup,
    ):
        # pylint: disable=R0914
        # Locals variables are here to simplify page parsing logic

        for cells in soup.find_all(
            "li", class_="ts-offer-list-item offerlist-item"
        ):
            # Extract title, ref and field
            title_ref_field = soup.find("a")["title"]
            title_ref, field = title_ref_field.split(" - ")
            title, ref = title_ref.split("(Réf. :")
            ref = ref[:-1].strip()

            # Extract localisation and job type
            desc = cells.find("ul", class_="ts-offer-list-item__description")
            items = desc.find_all("li")
            post_date = items[1].get_text(strip=True)
            contract_type = items[2].get_text(strip=True)
            localisation = items[3].get_text(strip=True)

            # Extract url
            url = cls.get_base_url() + str(cells.find("a")["href"])

            kwargs = {
                "field": field,
                "contract_type": contract_type,
                "url": url,
                "localisation": localisation,
                "title": title,
                "reference": ref,
                "post date": post_date,
            }
            offers.append(CiradScrapper(**kwargs))


if __name__ == "__main__":
    result = CiradScrapper.interrogate_website()
    CiradScrapper.analyse_jobs(
        *result,
        keywords={"Informatique": ["Informatique", "Informatic"]},
        localisations=["Montpellier, France", "Lyon, France"],
    )
    CiradScrapper.quick_display_list_of_offers(result)
