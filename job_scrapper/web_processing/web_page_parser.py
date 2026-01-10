from typing import Iterator
from urllib.parse import urlparse

import bs4
from bs4 import BeautifulSoup
from selenium.common.exceptions import (
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options

from job_scrapper.tools.secondary_logger_user import SecondaryLoggerUser, logging
from job_scrapper.web_processing.enhanced_chrome_browser import EnhancedChrome, PreparePage
import time
from contextlib import contextmanager
from urllib3.exceptions import ReadTimeoutError

class WebPageProcessor(SecondaryLoggerUser):
    """
    Contains a number of method that helps with the usage of
    EnhancedChrome. This class act as a rate limiter.
    """

    def __init__(
            self,
            logger: logging.Logger | None=None,
            chrome_options: Options | None=None,
            add_default_experimental_options: bool=True,
            rate_limit: int = 2,
            hide_web_driver: bool = True,
            default_page_preparation: PreparePage | None = None
    ):
        """
        :param logger: A logger
        :param chrome_options: Options for the browser. This object might
            be modified due to `add_default_experimental_options`
        :param add_default_experimental_options:
                If True, Some experimental options will be added to chrome_options.
               `options`. This will alter chrome_options. Without these options, some methods might break.
                add_default_experimental_options can not be changed after initialization.
        :param rate_limit: Minimal interval between two call to the same website.
        """
        super().__init__(logger)

        # Will add experimental opt to chrome_options
        # When a browser is created at this point
        # the Option passed as chrome_options will
        # be updated with these option
        self._add_default_experimental_options = add_default_experimental_options
        self.wait_between_calls = rate_limit
        self.all_cals: dict[str, float] = {}

        if chrome_options:
            self.chrome_options = chrome_options
        else:
            self.chrome_options = Options()
            if hide_web_driver:
                self.chrome_options.add_argument(
                    "--headless"
                )

        self.default_page_preparation = default_page_preparation

    @property
    def add_default_experimental_options(self):
        """ If True, Some experimental options will be added to self.chrome_options.
        `options`. Without these options, some methods might break.
        add_default_experimental_options can not be changed after initialization."""
        return self._add_default_experimental_options

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
        if prepare_page is None:
            prepare_page = self.default_page_preparation

        with self.start_browser_on(url=url, retry=retry, failed_sleep=failed_sleep) as browser:
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

        browser = EnhancedChrome(
            options=self.chrome_options,
            logger=self.logger,
            add_default_experimental_options=self._add_default_experimental_options,
            rate_limiter=self.wait_before_calling
        )
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
        """Open url in a browser and manage errors."""
        if not exceptions:
            exceptions = []

        try:
            self.wait_before_calling(url)
            browser.get(url)

        except WebDriverException and ReadTimeoutError as exception:
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
