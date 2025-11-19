import os
import re
import shutil
import tempfile
import time
import zipfile
from typing import Iterator, Protocol, TypeVar, Generic, Literal
from urllib.parse import unquote, urlparse

import bs4
from bs4 import BeautifulSoup
from geopy.distance import geodesic  # type: ignore[import-untyped]
from geopy.exc import GeocoderServiceError  # type: ignore[import-untyped]
from geopy.geocoders import Nominatim  # type: ignore[import-untyped]
from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By, ByType
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as cond
from selenium.webdriver.support.ui import WebDriverWait
from tools.secondary_logger_user import SecondaryLoggerUser, logging
from web_processing.enhanced_chrome_browser import EnhancedChrome, PreparePage, ButtonFinder
import time
from contextlib import contextmanager
from tools.get_unique_path import get_unique_path

class WebPageProcessor(SecondaryLoggerUser):
    work_dir = tempfile.TemporaryDirectory()

    def __init__(
            self,
            logger: logging.Logger | None=None,
            chrome_options: Options | None=None,
            rate_limit: int = 2,
    ):
        super().__init__(logger)
        self.wait_between_calls = rate_limit
        self.all_cals: dict[str, float] = {}

        if chrome_options:
            self.chrome_options = chrome_options
        else:
            self.chrome_options = Options()
            self.chrome_options.add_argument(
                "--headless"
            )

        self.chrome_options.add_experimental_option(
            "prefs",
            {
                # Change default directory for downloads
                "download.default_directory": os.path.abspath(
                    self.work_dir.name
                ),
                # Auto download the file
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                # It will not show PDF directly in chrome
                "plugins.always_open_pdf_externally": True,
            },
        )

    def wait_before_calling(self, url: str):
        base_url = self.extract_baseurl(url)
        now = time.time()

        if base_url in self.all_cals:
            last_call = self.all_cals[base_url]
            delta = now - last_call
            sleep_time = self.wait_between_calls - delta
            if sleep_time > 0:
                time.sleep(sleep_time)
                now += sleep_time  # account for sleep in the timestamp

        self.all_cals[base_url] = now


    def extract_html_from(
            self,
            url: str,
            prepare_page: PreparePage | None = None,
            pre_preparation_wait_time: int = 0.5,
            post_preparation_wait_time: int = 0.5,
            retry: int = 2,
            failed_sleep: int = 5,


    ) -> bs4.BeautifulSoup:
        """
        Extract html from a url.
        :param url: url that lead to the page to parse
        :param Callable | None prepare_page: A method that will be called
        :param int pre_preparation_wait_time: How long the function sleep before using <prepare_page>.
        :param int post_preparation_wait_time:  How long the function sleep after having used <prepare_page>.
        :param int retry: see <start_browser_on> 'retry' option.
        :param int failed_sleep: see <start_browser_on> 'failed_sleep' option.
        :return: A html soup that represent the <self.block_of_interest> extracted from the url
        """

        with self.start_browser_on(url, retry=retry, failed_sleep=failed_sleep) as browser:
            time.sleep(pre_preparation_wait_time)

            if prepare_page:
                prepare_page(browser)

            time.sleep(post_preparation_wait_time)

            html = browser.page_source

        return BeautifulSoup(html, "html.parser")

    @contextmanager
    def start_browser_on(self, url: str, retry=2, failed_sleep: int=5) -> Iterator[EnhancedChrome]:
        """
        Create a new EnhancedChrome that load <url>. browser.quit() is call
        at the end of the context manager.
        :param str url: A url
        :param int retry: How many times this loading can be retried.
        :param int failed_sleep: How long the program wait if the browser
            fails to open <url>.
        :return: the EnhancedChrome
        """
        self.logger.debug("Starting Chrome on %s", url)

        browser = EnhancedChrome(options=self.chrome_options, logger=self.logger)
        self._start_browser_on(browser, url, retry, failed_sleep)

        yield browser

        self.logger.debug("Closing browser : '%s' (current url : %s)", browser, url)
        browser.quit()

    def _start_browser_on(
            self,
            browser: EnhancedChrome,
            url: str,
            retry: int,
            failed_sleep: int,
            exceptions: list[str] | None = None
    ) -> None:
        if not exceptions:
            exceptions = []

        try:
            self.wait_before_calling(url)
            browser.get(url)

        except WebDriverException as exception:
            # Warn user
            self.logger.warning(
                "An error occurred when '%s' try to opens '%s'. :"
                "\n%s"
                "\n%s retry left",
                browser, url,
                exception,
                retry
            )

            # Archive error
            exceptions.append(f"With {retry} retry left) :\n{exception}")

            if retry <= 0:
                # No retry left, All errors will be used to generate a message
                exception_string = "\n-------------------------\n".join(exceptions)
                msg = (f"Multiple exception during interrogation of '{url}' with '{browser}' : "
                       f"\n{exception_string}")
                self.logger.fatal(msg)
                raise WebDriverException(
                    msg
                )

            time.sleep(failed_sleep)

            return self._start_browser_on(browser, url, retry - 1, failed_sleep, exceptions)


    @staticmethod
    def extract_baseurl(url: str):
        """Extract the base url of a url."""
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        return base_url

    def download_html(self):
        pass

    def download_file(
            self,
            url: str,
            retry: int = 2,
            timeout: int = 360,
            failed_sleep: int=5,
    ) -> str | None:
        # https://stackoverflow.com/questions/43149534/selenium-webdriver-how-to-download-a-pdf-file-with-python

        download_dir = self.work_dir.name
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        filename = unquote(filename)  # Avoid encoding errors
        filepath = os.path.join(download_dir, filename)

        self.logger.debug(
            "Downloading file : %s\ntimeout=%s\tExpected path : %s",
            url,
            timeout,
            filepath,
        )

        browser = EnhancedChrome(options=self.chrome_options, logger=self.logger)
        self.wait_before_calling(url)

        i = 0
        try:
            browser.get(url)
            while not os.path.exists(filepath) and i < timeout:
                time.sleep(1)
                i += 1

        except WebDriverException as exception:
            self.logger.warning("%s\n%s retry left", exception, retry)
            if retry <= 0:
                self.logger.error(
                    "Multiple exception during interrogation of %s. \n%s",
                    url,
                    exception,
                )
                raise

            time.sleep(failed_sleep)
            return self.download_file(
                url=url,
                retry=retry - 1,
                timeout=timeout,
                failed_sleep=failed_sleep,
            )
        finally:
            browser.quit()

        if not os.path.exists(filepath):
            self.logger.error("Download failed : %s", filepath)
            if i >= timeout :
                raise FileExistsError(f"File download from '{url}' failed : timeout ({i} >= {timeout})")
            else:
                raise FileExistsError(f"File download from '{url}' failed : {filepath} does not exist.")

        self.logger.debug("Download completed : %s", filepath)
        return filepath

wpp = WebPageProcessor()
f = wpp.download_file(
    url="https://rh.inserm.fr/nous-rejoindre/Lists/Emploi%20ITA/"
        "Attachments/5758/MOTTA_Inge%cc%81nieur-e%20d'e%cc%81tudes%20en%20techniques%20biologiques_112025.pdf"
)
print(os.path.abspath(f))
time.sleep(20)


# wpp = WebPageParser(chrome_options=Options())
# bro = wpp.start_browser_on("https://umontpellier.nous-recrutons.fr/offres-emploi/")
# for item in bro.iter_through_pages_using_buttons(
#     prepare_page=lambda _: bro.scroll_down(),
#     button_finder={
#         "by": By.CSS_SELECTOR,
#         "button_id": "div.jet-filters-pagination__item.prev-next.next",
#     },
#     wait_after_prepare_page=2,
#     wait_scroll_to_view_button=2,
#     # By.CSS_SELECTOR, "div.jet-filters-pagination__link", 15
# ):
#     print(item)
#
# time.sleep(5)
