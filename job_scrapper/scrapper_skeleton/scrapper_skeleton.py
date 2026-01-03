"""
Skeleton for JobScrapperClass
"""
import os.path
from typing import Self, Iterator

import re
from .request_core import ScrapperRequestCore, KeywordManager, ExportBrowserPage, BeautifulSoup
from sql.tables.keywords.keyword_version import KeywordVersion, Session
import time
from datetime import datetime, timedelta
from selenium.common.exceptions import WebDriverException
from urllib.error import URLError, HTTPError

class JobScrapperSkeleton(ScrapperRequestCore):
    @classmethod
    def run(
            cls,
            contact: str,
            keywords_to_search: KeywordManager | None = None,
            page_exporter: ExportBrowserPage | None = None,
            tsv_export: bool = True,
            sql_export: bool = True,

            search_offer_text: bool = True,
            search_offer_html: bool = True,
            retry_offer_fetch: int = 2,
            failed_sleep: int = 5,

            re_inspect_after: int = 30,

            batch_export: int = 20,
            database_name: str | None = None,
            workdir: str | None = None,
    ):
        if not database_name:
            database_name = cls.DEFAULT_DATABASE

        if not workdir:
            workdir = cls.get_workdir()

        # Initialize geolocalisator with a contact.
        cls.logger.info("Initialisation of geopy rate limiter... (%s)", contact)
        cls.get_geolocator(contact)

        # Keyword management
        with cls.get_sql_session(workdir=workdir, database_name=database_name) as session:
            if keywords_to_search is None:
                cls.logger.info("Using default keywords to search configuration : Loading database...")
                keywords_to_search = KeywordManager(logger=cls.logger)
                keywords_to_search.load_all(session)

            else:
                # Ensure that all keywords version exist in database.
                keywords_to_search.commit(session)

        with cls.get_sql_session(workdir=workdir, database_name=database_name) as session:
            keyword_ver = keywords_to_search.versions(session)

        cls.logger.info(
            "%s keyword(s) found : \n%s",
            len(keyword_ver), "\n".join([f"{k}: {v}" for k, v in keyword_ver.items()])
        )

        tsv_folder = os.path.join(cls.get_class_dir(), "TSVs")
        if not os.path.exists(tsv_folder):
            os.mkdir(tsv_folder)
        tsv_file = cls.get_unique_path(os.path.join(tsv_folder, f"{cls.strftime(cls.now())}.tsv"))
        offer_batch = []
        i = 0
        ignored = 0
        inspection_failed = 0
        inspected = 0
        total = 0

        for i, offer in enumerate(cls.extract_offers_from_website()):
            if offer is None:
                # An offer should be ignored see extract_offers_from_website logging.
                offer_batch.append(None)
                ignored += 1
                continue

            cls.logger.debug("Processing offer %s : %s (%s)", i + 1, offer, offer.url)

            if (
                    keywords_to_search is None
                    and page_exporter is None
                    and search_offer_text is False
                    and search_offer_html is False
            ):
                # We do not need to run offer inspection,
                # There is nothing that should be inspected
                pass

            else:
                try:
                    cls.run_offer_inspection(
                        offer=offer,
                        offer_id=i,

                        global_page_exporter=page_exporter,
                        global_search_offer_html=search_offer_html,
                        global_keywords_to_search=keywords_to_search,
                        global_search_offer_text=search_offer_text,

                        re_inspect_after = re_inspect_after,
                        retry_offer_fetch = retry_offer_fetch,
                        failed_sleep = failed_sleep,

                    )
                    inspected += 1

                except HTTPError and URLError and WebDriverException as e:
                    cls.logger.error(
                        "Unable to inspect offer %s : %s (%s)",
                        i + 1, offer, offer.url
                    )
                    inspection_failed += 1

            total += 1
            offer_batch.append(offer)

            if len(offer_batch) >= batch_export:
                cls.run_exportation(
                    sql_export=sql_export,
                    tsv_export=tsv_export,
                    tsv_file=tsv_file,
                    offer_batch=offer_batch,
                    i=i,
                    keyword_ver=keyword_ver,
                    database_name=database_name,
                    workdir=workdir
                )
                offer_batch.clear()


        # Ensure that all items in offer_batch
        # Have been exported
        cls.run_exportation(
            sql_export=sql_export,
            tsv_export=tsv_export,
            tsv_file=tsv_file,
            offer_batch=offer_batch,
            i=i,
            keyword_ver=keyword_ver,
            database_name=database_name,
            workdir=workdir
        )

        cls.logger.info(
            "%s.run have succeed with %s offers found !\n"
            "- %s offer(s) inspected.\n"
            "- %s offer(s) have failed their(s) inspection.\n" 
            "- %s listing entry ignored due to redundancy in said listing.",
            cls.get_standardised_class_name(), total,
            inspected,
            inspection_failed,
            ignored,
        )

    @classmethod
    def run_exportation(
            cls,
            sql_export: bool,
            tsv_export: bool,
            tsv_file: str,
            offer_batch: list[Self],
            i: int,
            keyword_ver: dict[str, KeywordVersion],

            database_name: str | None = None,
            workdir: str | None = None,


    ):
        if not any(x is not None for x in offer_batch):
            return

        if sql_export:
            cls._run_export_sql(
                offer_batch=offer_batch,
                database_name=database_name,
                workdir=workdir,
                i=i,
                keywords_ver=keyword_ver,
            )
        if tsv_export:
            cls._run_export_tsv(
                offer_batch=offer_batch,
                i=i,
                tsv_file=tsv_file,
            )
        offer_batch.clear()

    @classmethod
    def run_offer_inspection(
            cls,
            offer: Self,
            offer_id: int,

            global_keywords_to_search: KeywordManager | None = None,
            global_page_exporter: ExportBrowserPage | None = None,
            global_search_offer_text: bool = True,
            global_search_offer_html: bool = True,

            retry_offer_fetch: int = 2,
            failed_sleep: int = 5,
            re_inspect_after: int = 30,
    ) -> bool:
            # Apply timestamp constraint
            (
                offer_keywords_to_search,
                offer_page_exporter,
                offer_search_offer_text,
                offer_search_offer_html
            ) = cls._apply_time_stamp_constraint(
                offer=offer,
                offer_id=offer_id,

                keywords_to_search=global_keywords_to_search,
                page_exporter=global_page_exporter,
                search_offer_text=global_search_offer_text,
                search_offer_html=global_search_offer_html,

                re_inspect_after=re_inspect_after,
            )

            # Avoid necessary requests
            if (
                    offer_keywords_to_search is None
                    and offer_page_exporter is None
                    and offer_search_offer_text is False
                    and offer_search_offer_html is False
            ):
                cls.logger.info(
                    "Ignoring processing of offer number %s ('%s' - '%s') since  all the inspections that needed to be "
                    "performed were already completed less than %s days ago.",
                    offer_id + 1, offer, offer.url, re_inspect_after
                )

                return False


            cls.logger.info(
                "Proceeding with the inspection of offer number %s ('%s' - '%s')",
                offer_id + 1, offer, offer.url
            )
            offer.offer_inspection(
                keywords_to_search=offer_keywords_to_search,
                page_exporter=offer_page_exporter,
                search_offer_html=offer_search_offer_text,
                search_offer_text=offer_search_offer_html,
                retry=retry_offer_fetch,
                failed_sleep=failed_sleep,
            )
            return True



    @classmethod
    def _run_export_tsv(
            cls,
            offer_batch: list[Self | None],
            i: int,
            tsv_file: str,
    ):
        offer_to_text, offer_list = cls._run_export_clean(
            offer_batch=offer_batch,
            i=i
        )

        cls.logger.info("Proceeding to tsv exportation of %s offers :\n"
                         "%s",
                         len(offer_list),
                         f"{offer_to_text}"
        )
        cls.batch_export_to_flat_file(jobs=offer_list, file_path=tsv_file, mod="a")

    @classmethod
    def _run_export_sql(
            cls,
            offer_batch: list[Self | None],
            database_name: str,
            workdir: str,
            i: int,
            keywords_ver: dict[str, KeywordVersion] | None = None


    ):
        offer_to_text, offer_list = cls._run_export_clean(
            offer_batch=offer_batch,
            i=i
        )

        cls.logger.info("Proceeding to sql exportation of %s offers :\n"
                         "%s",
                         len(offer_list),
                         f"{offer_to_text}"
        )
        cls.sql_batch_export(
            *offer_list,
            database_name=database_name,
            workdir=workdir,
            keywords_ver=keywords_ver,
        )

    @classmethod
    def _run_export_clean(
            cls,
            offer_batch: list[Self | None],
            i: int
    ) -> tuple[str, list[Self]]:
        offer_to_text = ""
        offer_list = []

        for oi, offer in enumerate(offer_batch):
            if offer is None:
                continue

            index = (i + 1) - len(offer_batch) + (oi + 1)
            offer_to_text += f"{index} ({offer} - {offer.url})\n"
            offer_list.append(offer)

        return offer_to_text, offer_list


    @classmethod
    def _apply_time_stamp_constraint(
            cls,
            offer: Self,
            offer_id: int,

            keywords_to_search: KeywordManager | None = None,
            page_exporter: ExportBrowserPage | None = None,
            search_offer_text: bool = True,
            search_offer_html: bool = True,
            re_inspect_after: int = -1,
    ) -> tuple[
        KeywordManager | None,
        ExportBrowserPage | None,
        bool,
        bool
    ]:
        threshold = datetime.now() - timedelta(days=re_inspect_after)
        msg = []

        if keywords_to_search is not None and offer.timestamp_is_too_old(offer.URLInspectionTimeStamp.KEYWORD, threshold):
            keywords_to_search = None
            msg.append("Keyword research.'")

        if page_exporter is not None and offer.timestamp_is_too_old(offer.URLInspectionTimeStamp.DOWNLOAD, threshold):
            page_exporter = None
            msg.append("Offer downloading.'")

        if offer.timestamp_is_too_old(offer.URLInspectionTimeStamp.TEXT, threshold):
            search_offer_text = False
            msg.append("Offer's text parsing.")

        if offer.timestamp_is_too_old(offer.URLInspectionTimeStamp.HTML, threshold):
            search_offer_html = False
            msg.append("Offer's HTML parsing'.")

        if msg:
            cls.logger.info(
                "Ignoring step(s) realised less than %s days ago during offer processing of '%s' (%s): "
                "\n-\t%s"
                "\nThreshold date is '%s'",
                re_inspect_after,   offer, offer_id + 1,
                "\n-\t".join(msg),
                threshold,
            )

        return keywords_to_search, page_exporter, search_offer_text, search_offer_html

    # TOOLS
    @staticmethod
    def _try_to_find_field__remove_link_word(field: str) -> str:
        link_words = [
            "en", "de", "des", "d", "à", "pour", "avec", "sans",
            "sur", "sous", "dans", "par", "entre", "chez",
            "vers", "contre", "après", "avant", "depuis", "pendant",
            "selon", "malgré", "parmi", "envers", "hors", "sauf",
            "jusque", "via", "et", "ou", "mais", "donc",
            "or", "ni", "car", "au", "un", "une", "le", "la", "les"
        ]

        pattern = r"\b(?:%s)\b\s?" % "|".join(link_words)

        return re.sub(pattern, "", field, flags=re.IGNORECASE)

    # TOOLS
    @classmethod
    def _try_to_find_field__employment_type_word(cls, field: str) -> str:
        employment_type_word = [
            r"ingénieur(e)?\s?",
            r"technicien(ne)?\s?",
            r"assistant(e)?\s?",
            r"chercheur(se)?\s?",
            r"doctorant(e)?\s?",
            r"post[- ]?doctorant(e)?\s?",
            r"postdoc\s?",
            r"stagiaire\s?",
            r"stage\s?",
            "cdd\s?",
            "cdi\s?",
            "m1\s?",
            "m2\s?",
            "l1\s?",
            "l2\s?",
            "l3\s?",
            r"alternant(e)?\s?",
            r"alternance\s?",
            r"apprenti(e)?\s?",
            r"chargé(e)? de recherche\s?",
            r"chef(fe)? de projet\s?",
            r"responsable\s?",
            r"manager\s?",
            r"superviseur(e)?\s?",
            r"coordinateur(trice)?\s?",
            r"analyste\s?",
            r"consultant(e)?\s?",
            r"développeur(se)?\s?",
            r"enseignant(e)?\s?",
            r"professeur(e)?\s?",
            r"technologue\s?",
            r"opérateur(trice)?\s?",
            r"agent(e)?\s?",
        ]
        pattern = "|".join(employment_type_word)
        cls.logger.critical("%s         %s", field, pattern)
        f =  re.sub(pattern, "", field, flags=re.IGNORECASE)
        cls.logger.critical("%s", f)
        return f

    @classmethod
    def try_to_find_field(cls, title: 'JobScrapperSkeleton | str'):
        """In those offers, the field is not always obvious to parse.
        This method tries to find it by parsing the title."""

        if isinstance(title, str):
            field = title
        else:
            field = title.title


        field = field.lower()
        if " - " in field:
            # Remove prefixes : "50238 - "; "IBODE -"
            field = " ".join(field.split(" - ")[1:])

        # Remove H/F Mention.
        field = re.sub(
            r"\b[hf]\s?[/\-]\s?[hf]\b",
            "",
            field,
            flags=re.IGNORECASE
        )

        field = re.sub(
             r"\b(?:hf|fh)\b",
            "",
            field,
            flags=re.IGNORECASE
        )

        # Remove employment like words
        field = cls._try_to_find_field__employment_type_word(field)

        # Remove all link word
        field = cls._try_to_find_field__remove_link_word(field)

        # The first two words generally gives
        # a good idea of the field
        field = " ".join(field.split(" ")[:2])

        # If the first world contains a dash
        # the first world is generally enough
        field = "-".join(field.split("-")[:2])

        if len(field.replace(" ", "")) < 5:
            # This string is really short, we might have
            # no information inside it.
            return None
        return field

    def timestamp_is_too_old(
            self,
            ts_type: ScrapperRequestCore.URLInspectionTimeStamp,
            threshold: datetime
    ) -> bool:
        if not self.time_stamps_exist(ts_type):
            return False

        ts = self.retrieve_time_stamps(self.URLInspectionTimeStamp.DOWNLOAD)
        dt = datetime.fromtimestamp(time.mktime(ts))
        return threshold <= dt

    # QUESTIONS
    @classmethod
    def get_offer_listing_url(cls) -> str:
        """Returns a url that lead to an online listing of offers."""
        raise NotImplementedError

    def get_expected_download_time(self) -> int:
        """If offers on the scrapped website are contained inside files
        (pdf ...), the file should be downloaded.
        This function says how long the download is expected to take.
        Returns -1 if no download (file) is expected."""
        raise NotImplementedError

    @classmethod
    def iter_trough_offer_listing(cls, url: str) -> Iterator["Self"]:
        """Iter through each pages of the online listing <get_offer_listing_url>.
        If you need to (re)write this method the simplest method are :

        When only one page is expected:
            - `cls.get_web_processor().extract_block_on_one_page(url)`

        When the url contains the page number :
            - `cls.get_web_processor().extract_block_across_multiple_pages_using_url(url)`

        When the url does not contain the page number:
            - `cls.get_web_processor().extract_block_across_multiple_pages_using_buttons(
                url,
                button_finder
            )`

            with `button_finder`:
                A. Function  (driver: "EnhancedChrome"() -> WebElement | None)
                    that find the button that can
                    be clicked to  load the next page. Generally a lambda
                    that trigger <browser.get_next_page_button>.
                B. Use a dictionary if you want to use <self.get_next_page_button>
                   as <button_finder>. In this case, make sure that the dict contains
                        - by: ByType,
                        - button_id: str,

        """
        raise NotImplementedError

    @classmethod
    def find_offer_listing_on_page(cls, soup: BeautifulSoup) -> BeautifulSoup:
        """Should return a BeautifulSoup that only contains the offer listing.
        (This soup should not contain webpage header / footer other metadata.)"""

        raise NotImplementedError

    @classmethod
    def generate_offer_from_listing(cls, soup: BeautifulSoup) -> Iterator[Self]:
        """Generate a number of scrapper object from a block of HTML code that
        should correspond to the listing of offers."""
        raise NotImplementedError

    def pget_expected_geopy_country_code(self) -> list[str | None]:
        """Returns a list of country code that can help geopy / Nominatim
        to figure the right coordinate of self.localisation.
        You can use ISO 3166-1 alpha-2 country codes
        (https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2#Officially_assigned_code_elements)

        Geopy will only search inside country code that are listed here. You can use
        `None` in the returned list to search without geographic restrictions.

        return ["FR", None] --> Search in France then all around the world
        return ["FR", "UM"] --> Search in France then United States
        return ["FR", "UM", None] --> Search in France then United States then  all around the world
        """
        raise NotImplementedError
