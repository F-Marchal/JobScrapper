"""
Skeleton for JobScrapperClass
"""

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
