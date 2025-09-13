"""
Skeleton for JobScrapperClass
"""

import json
import os.path
from contextlib import contextmanager

from bs4 import BeautifulSoup

from .request_core import ScrapperRequestCore

class JobScrapperSkeleton(ScrapperRequestCore):
    """
    Skeleton for JobScrapperClass. Those class should be able to :
    - Represent a job offer
    - Scrap a website to extract job offer
    - Parse job offer url to find more intel on the offer
    - Compute a distance between a location and the offer
    """

    @classmethod
    def extract_block_of_interest(cls, soup) -> BeautifulSoup:
        """
        Extract a block of html that contain the job offers.
        """
        raise NotImplementedError("Should be reimplemented when inherited")

    @classmethod
    def complete_job_page_parsing(
        cls,
        offers: list["ScrapperRequestCore"],
        soup,
    ):
        """Scrap <cls.website_url> to find a number of job offer.
        Those job offer are stored inside 'offers'.
        :param offers: A list of job offer
        :param soup: A Beautiful soup object (html)
        :return:
        """
        raise NotImplementedError("Should be reimplemented when inherited")

    class ConfigurationFile:
        """
        A file that represent a configuration file used by JobScrapperSkeleton.
        """

        def __init__(self, logger, path: str | None, name: str, workdir: str):
            """
            :param logger: The same logger as the JobScrapperSkeleton that create it
            :param path: path that lead to the configuration file
            :param name: the default name of this configuration file
            :param workdir: The same workdir as the JobScrapperSkeleton that create it
            """
            self.workdir = workdir
            self.logger = logger
            self.name = name
            self.path = path

        def find_file_path(self, path: str | None):
            """
            When path is str:
                - Ensure that the path lead to a file
            When path is None:
                - Try to generate a default path to use instead of None.
            :param path: A path that lead to a json
            :return:
            """
            if path:
                if os.path.exists(path) and not os.path.isfile(path):
                    raise FileNotFoundError(
                        f"{path} is not a file. Can not load or create {self.name}."
                    )

                self.logger.info("'%s' will be used as '%s'.", path, self.name)
                return path
            fallback_path = os.path.join(self.workdir, self.name + ".json")
            return self.find_file_path(fallback_path)

        @property
        def path(self) -> str:
            """Path of this file"""
            return self._path

        @path.setter
        def path(self, value):
            """Set the path of this file using self.find_file_path(value)"""
            self._path = self.find_file_path(value)

        def load(self):
            """Load the content of self.path. if self.path do not exist, None is returns"""
            if not os.path.exists(self.path):
                return None
            with open(self.path, "r", encoding="utf-8") as file:
                return json.load(file)

        def dump(self, data):
            """Dump data into a json file using self.path"""
            with open(self.path, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)

    #
    @classmethod
    @contextmanager
    def full_setup(
        cls,
        localisations_to_search_json: None | str = None,
        keywords_to_search_json: str | None = None,
        known_localisations_json: str | None = None,
        known_urls_json: str | None = None,
        dumb_urls: bool = True,
        dump_localisations: bool = True,
    ):
        """
        Use this with the <with> statement to manage the configuration files. The files will
        be parsed and output as dict / list or sets. When the with statement will end. The content of each
        file will be updated.
        ```python3
        with JobScrapperSkeleton.full_setup(*args) as (lts, kts, kl, ku):
            # Functions using those configurations files
        ```
        :param str or None localisations_to_search_json: A json (list[str]) that contain a list of places.
            The distances between those places and the offer will be estimated.
        :param str or None keywords_to_search_json: A json (dict[str, list[str]]) that contain a
            dictionary of keywords. Each keyword is searched inside the offer a counted.
        :param str or None known_localisations_json: A json (dict[str, tuple[float, float]]) that contain
          a dictionary of known localisations : "localisation1": (latitude, longitude)
        :param str or None known_urls_json: A json that contain a list[str] of url that should not be parsed.
            Each job object with its url in this set will be ignored.
        :param bool dumb_urls: Do known_urls_json is updated with new localisations ?
            (Default True)
        :param bool dump_localisations: Do known_localisations_json file is updated with new localisations ?
            (default True)
        """
        # pylint: disable=R0914
        # Locals variables help me to understand my code

        if not os.path.isdir(cls.workdir):
            cls.logger.info("Creation of %s", cls.workdir)
            os.mkdir(cls.workdir)

        localisations_search_file = cls.ConfigurationFile(
            name="researched-localisation",
            path=localisations_to_search_json,
            logger=cls.logger,
            workdir=cls.workdir,
        )
        keywords_search_file = cls.ConfigurationFile(
            name="researched-keywords",
            path=keywords_to_search_json,
            logger=cls.logger,
            workdir=cls.workdir,
        )
        known_localisations_file = cls.ConfigurationFile(
            name="known-localisation",
            path=known_localisations_json,
            logger=cls.logger,
            workdir=cls.workdir,
        )
        known_urls_file = cls.ConfigurationFile(
            name="known-urls",
            path=known_urls_json,
            logger=cls.logger,
            workdir=cls.workdir,
        )

        tmp_lts: list[str] | None = localisations_search_file.load()
        tmp_kts: dict[str, list[str]] | None = keywords_search_file.load()
        tmp_kl: dict[str, tuple[float, float]] | None = (
            known_localisations_file.load()
        )
        tmp_kut: list[str] | None = known_urls_file.load()

        localisations_to_search: list[str] = tmp_lts if tmp_lts else []
        keywords_to_search: dict[str, list[str]] = tmp_kts if tmp_kts else {}
        known_localisations: dict[str, tuple[float, float]] = (
            tmp_kl if tmp_kl else {}
        )
        ku_tmp: list[str] = tmp_kut if tmp_kut else []
        known_urls: set[str] = set(ku_tmp)

        yield localisations_to_search, keywords_to_search, known_localisations, known_urls

        cls.logger.debug("Save configurations files' state")
        if dump_localisations:
            known_localisations_file.dump(known_localisations)

        if dumb_urls:
            known_urls_file.dump(list(known_urls))

        # localisations_search_file.dump(localisations_to_search)
        # keywords_search_file.dump(keywords_to_search)

    @classmethod
    def main(
        cls,
        # Setting
        localisations_to_search_json: None | str = None,
        keywords_to_search_json: str | None = None,
        known_localisations_json: str | None = None,
        known_urls_json: str | None = None,
        # Export methods
        sql_export: bool = True,
        display: bool = True,
        flat_export: str | None = None,
        save_job_page: bool = False,
        dumb_urls: bool = True,
        dump_localisations: bool = True,
    ) -> list[ScrapperRequestCore]:

        with cls.full_setup(
            localisations_to_search_json,
            keywords_to_search_json,
            known_localisations_json,
            known_urls_json,
            dumb_urls=dumb_urls,
            dump_localisations=dump_localisations,
        ) as (lts, kts, kl, ku):
            result = cls.interrogate_website()
            cls.analyse_jobs(
                *result,
                keywords=kts,
                localisations=lts,
                known_localisations=kl,
                known_urls=ku,
                save_job_page=save_job_page,

            )

            cls.logger.info("%s analysis done.", len(result))

        if flat_export:
            if os.path.exists(flat_export) and not os.path.isfile(flat_export):
                cls.logger.warning(
                    "Can not export jobs to '%s'. The export will be done in the terminal. ",
                    flat_export,
                )
                display = True
            else:
                cls.logger.info(
                    "Starting the export of %s jobs in '%s'",
                    len(result),
                    flat_export,
                )
                cls.list_to_flat_file(flat_export, result)

        if display:
            cls.logger.info("Starting display of %s jobs", len(result))
            cls.complete_display_list_of_offers(result)

        if sql_export:
            cls.logger.info(
                "Starting export into the sql database of %s jobs", len(result)
            )
            cls.list_to_sql(result)

        return result
