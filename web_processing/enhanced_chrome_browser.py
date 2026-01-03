import os
import tempfile
import time

from typing import Iterator, Protocol, Optional
from urllib.parse import unquote, urlparse
from tools.get_unique_path import get_unique_path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import ByType
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as cond
from selenium.webdriver.support.ui import WebDriverWait
from tools.secondary_logger_user import SecondaryLoggerUser, logging
from selenium.webdriver.chrome.service import Service


class ButtonFinder(Protocol):
    """Function type that can be used to detect a button on a webpage.

    TODO: Expected behavior"""
    def __call__(self, driver: "EnhancedChrome") -> WebElement | None: ...

class ButtonFinderIterator(Protocol):
    """Function type that can be used to detect a button on a webpage.

    TODO: Expected behavior"""
    def __call__(self, driver: "EnhancedChrome") -> Iterator[WebElement | None]: ...

class PreparePage(Protocol):
    """Function type that can be used to prepare a page before parsing it."""
    def __call__(self, driver: "EnhancedChrome") -> None: ...

class WebRateLimiter(Protocol):
    def __call__(self, url: "str") -> None: ...

class EnhancedChrome(webdriver.Chrome, SecondaryLoggerUser):
    """
    A webdriver.Chrome extended to contain methods widely use
    by job scrappers to parse web pages.
    """
    def __init__(
            self,
            rate_limiter: WebRateLimiter,
            options: Optional[Options] = None,
            service: Optional[Service] = None,
            keep_alive: bool = True,
            logger: logging.Logger | None = None,
            add_default_experimental_options: bool = True,
    ):
        """
        :param options:  Optional Options to configure how this browser works.
            /!\\ if  `add_default_experimental_options` is True, this Options object
            will be modified at the initialization of this object.
        :param service: see webdriver.Chrome.__init__ 's service argument
        :param keep_alive: see webdriver.Chrome.__init__ 's keep_alive argument
        :param logger: An optional Logger to display logs and errors.
        :param add_default_experimental_options: If True, Some experimental options will be added to
            `options`. Without these options, some methods might break.
        """
        self._rate_limiter = rate_limiter

        if options is None:
            options = Options()

        self._workdir = tempfile.TemporaryDirectory()
        if add_default_experimental_options:
            options.add_experimental_option(
                "prefs",
                {
                    # Change default directory for downloads
                    "download.default_directory": os.path.abspath(
                        self.workdir
                    ),
                    # Auto download the file
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    # It will not show PDF directly in chrome
                    "plugins.always_open_pdf_externally": True,
                },
            )

        super().__init__(options=options, service=service, keep_alive=keep_alive)
        SecondaryLoggerUser.__init__(self, logger)

    @property
    def rate_limiter(self) -> WebRateLimiter:
        return self._rate_limiter

    def wait_to_respect_rate_limitation(self):
        self.rate_limiter(self.current_url)

    def quit(self) -> None:
        super().quit()
        self._workdir.cleanup()

    @property
    def workdir(self) -> str:
        """Temporary workdir path"""
        return self._workdir.name

    # Page movement
    def scroll_to_bottom(self) -> None:
        """Scroll a page until the end of said page to see the bottom of it."""
        self.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )

    def scroll_to_view(self, element: WebElement) -> None:
        """
        Scroll a page to show an `element` in the center of said page.
        """
        self.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", element
        )
    # Page movement

    # Pop-ups management
    def close_pop_up(
            self,
            selector: ByType,
            button_id: str,
            timeout: int = 15,
    ):
        """
        Close a potential popup (such as cookie pop up) that a website might display.
        :param selector: How to identify the 'clos po pup' button
        :param button_id: 'clos po pup' button identifier
        :param timeout: How long do we to see the 'clos po pup'.
        """
        try:
            pop_up = self.wait_until_clickable(selector, button_id, timeout)
            pop_up.click()
        except TimeoutException as te:
            raise WebDriverException(
                f"Unable to find targeted popup in time ({timeout}sec) : '{button_id}' ({selector}). ({te})"
            )

    def safe_close_pop_up(
            self,
            *args,
            **kwargs,
    ) -> bool:
        """Same as `close_pop_up` but no error will be raised when time is out.
        Returns False when time is out. Otherwise, True is returned."""
        try:
            self.close_pop_up(*args, **kwargs)
            return True
        except TimeoutException as te:
            self.logger.debug("Exception catch by safe_close_pop_up : %s", te)
            return False
    # Pop-ups management

    # Page navigation
    def wait_until_clickable(
            self,
            selector: ByType,
            element_id: str,
            timeout: int = 15,
            **kwargs
    ):
        """Wait until a web element can be clicked.
        :param selector: How to identify web element.
        :param element_id: web element identifier
        :param timeout: How long until we considered that the button can not be found.
        :param kwargs: Other options for WebDriverWait.
        """
        self.logger.debug(
            "Waiting %s seconds in order to find '%s' (%s). url=%s",
            timeout, element_id, selector, self.current_url
        )
        obj = WebDriverWait(self, timeout, **kwargs).until(
            cond.element_to_be_clickable((selector, element_id))
        )
        return obj

    def safe_wait_until_clickable(
            self,
            selector: ByType,
            element_id: str,
            timeout: int = 15,
    ) -> WebElement | None:
        """Seme as  `wait_until_clickable`  but no error will be raised when time is out, instead None is returned.
        :param selector: How to identify web element.
        :param element_id: web element identifier
        :param timeout: How long until we considered that the button can not be found.
        """
        try:
            self.wait_until_clickable(selector=selector, element_id=element_id, timeout=timeout)

        except TimeoutException as te:
            self.logger.debug("Can not find '%s' (%s). %s", element_id, selector, te)
            return None

    def iter_through_pages_using_buttons(
            self,
            button_finder: ButtonFinder | dict[str, ByType | int | str],
            prepare_page: PreparePage | None = None,

            wait_after_prepare_page: int = 0.5,
            wait_scroll_to_view_button: int = 0.5,
    ) -> Iterator[BeautifulSoup]:
        """
        Iterator that contains a number of BeautifulSoup HTML code.
        :param button_finder:
            A. Function that find the button that can
                be clicked to  load the next page. Generally a lambda
                that trigger <get_next_page_button>.
            B. Use a dictionary if you want to use <self.get_next_page_button>
               as <button_finder>. In this case, make sure that the dict contains
                    - by: ByType,
                    - button_id: str,
        :param prepare_page: A function that prepare page each web pages.
            Default : self.scroll_down
        :param int wait_after_prepare_page: How long (sec) should the
            function wait after <prepare_page> was run.
        :param int wait_scroll_to_view_button: How long (sec) should the
            function wait for press the button that go to page.
        """

        # Loop variables
        is_enabled = True
        i = 1

        while is_enabled:
            # Extract current page html
            yield self._iter_through_pages_using_button__extract_html(
                prepare_page=prepare_page,
                wait_after_prepare_page=wait_after_prepare_page,
            )

            # ---------- Find button state --------------
            self.logger.debug("Seeking 'next' button on page %s using %s", i, button_finder)
            if isinstance(button_finder, dict):
                next_page_btn = self.safe_wait_until_clickable(**button_finder)
            else:
                next_page_btn = button_finder(self)
            is_enabled = next_page_btn is not None
            # --------------------------------------------

            # Load next page
            if is_enabled:
                self.logger.debug("'next' button found on page %s : %s ", i, next_page_btn)
                self.scroll_to_view(next_page_btn)
                time.sleep(wait_scroll_to_view_button)
                self.wait_to_respect_rate_limitation()
                next_page_btn.click()

            else:
                self.logger.debug("No 'next' button found on page %s ! Quitting page iteration ", i)

            i += 1

    def iter_through_pages_using_button_iterator(
            self,
            button_finder: ButtonFinderIterator,
            prepare_page: PreparePage | None = None,

            wait_after_prepare_page: int = 0.5,
            wait_scroll_to_view_button: int = 0.5,
    ) -> Iterator[BeautifulSoup]:
        """
        Iterator that contains a number of BeautifulSoup HTML code.
        :param button_finder:

            TODO: update
            OLDD : An iterator function that find the button that load the
            next page. All pages are parsed from the first (before any button
            has been clicked) to the last (after last button has been clicked).
        :param prepare_page: A function that prepare page each web pages.
            Default : self.scroll_down
        :param int wait_after_prepare_page: How long (sec) should the
            function wait after <prepare_page> was run.
        :param int wait_scroll_to_view_button: How long (sec) should the
            function wait for press the button that go to page.
        """

        # Loop variables
        i = 1

        for next_page_btn in button_finder(self):
            # Extract current page html
            yield self._iter_through_pages_using_button__extract_html(
                prepare_page=prepare_page,
                wait_after_prepare_page=wait_after_prepare_page,
            )

            if next_page_btn is None:
                continue

            # Go to next page
            self.logger.debug("'Next' button found on page %s : %s ", i, next_page_btn)
            self.scroll_to_view(next_page_btn)
            time.sleep(wait_scroll_to_view_button)
            self.wait_to_respect_rate_limitation()
            next_page_btn.click()


    def _iter_through_pages_using_button__extract_html(
            self,
            prepare_page: PreparePage | None = None,
            wait_after_prepare_page: int = 0.5,
    ) -> BeautifulSoup:
        if prepare_page:
            self.wait_to_respect_rate_limitation()
            prepare_page(self)
        time.sleep(wait_after_prepare_page)

        return BeautifulSoup(self.page_source, "html.parser")

    # Page navigation

    @classmethod
    def get_download_file_path_for(
            cls,
            url: str,
            download_dir: str,
            ext: str = None
    ):
        """
        Give the probable file path for a file download
        :param url: Url of said file.
        :param download_dir: Where the download should take place
        :param ext: File extension
        :return:
        """
        download_dir = cls.workdir if not download_dir else download_dir
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename:
            # This can happen when url end with a "/".
            # In this case we use 'directory' name
            filename = os.path.basename(os.path.dirname(parsed_url.path))
        filename = unquote(filename)  # Avoid encoding errors
        return get_unique_path(os.path.join(download_dir, filename), ext)

    def get_download_file_path(
            self,
            download_dir: str = None,
            ext: str = None
    ):
        """
        Give the probable file path for a file download
        :param str download_dir: Where the download should take place
        :param str ext: File extension
        :return:
        """
        if download_dir is None:
            download_dir = self.workdir

        return self.get_download_file_path_for(self.current_url, download_dir=download_dir, ext=ext)

    def take_snapshot(self) -> dict[str, str]:
        """Returns current url as mhtml dict"""
        return self.execute_cdp_cmd("Page.captureSnapshot", {"format": "mhtml"})

    def save_snapshot(self, workdir: str | None=None) -> str:
        """Save current url as mhtml file in workdir. If workdir is None
        self.workdir is used."""
        content = self.take_snapshot()

        file_path = self.get_download_file_path(
            workdir,
            ext=".mhtml"
        )

        with open(file_path, "w", encoding="utf-8") as flux:
            flux.write(content["data"])

        return file_path

    def save_raw_html(self, workdir: str | None=None) -> str:
        """Save raw html in workdir. If workdir is None
        self.workdir is used."""
        filepath = self.get_download_file_path(
            download_dir=workdir,
            ext=".html"
        )

        with open(filepath, "w", encoding="utf8") as flux:
            flux.write(self.page_source)

        return filepath

    def wait_for_file_download_completion(
            self,
            workdir: str | None=None,
            timeout: int = 360,
            sleep_interval: int = 1,
    ) -> str:
        """
        Wait a certain time until a file has been downloaded. This file is supposed
        to be the one self.current_url point to.
        The function will wait until this file exist in `workdir` or timeout is passed.
        :param workdir: If workdir is None self.workdir is used.
        :param timeout: How long before we abandon the download (Will raise FileExistsError if download
            completion is still in progress / failed).
        :param sleep_interval: How frequent the program check if the file exist.
        :return:
        """
        # Warnings :  only one time, file displacement
        url = self.current_url
        ext = os.path.splitext(url)[1]
        filepath = self.get_download_file_path(workdir, ext=ext)

        self.logger.debug(
            "Downloading file : %s\ntimeout=%s\tExpected path : %s",
            url,
            timeout,
            filepath,
        )

        start_time = time.time()
        delta = 0
        while not os.path.exists(filepath) and delta < timeout:
            time.sleep(sleep_interval)
            current_time = time.time()
            delta = current_time - start_time

        if not os.path.exists(filepath):
            self.logger.error("Download failed : %s", filepath)
            if delta >= timeout :
                raise FileExistsError(f"File download from '{url}' failed : timeout ({delta} >= {timeout})")
            else:
                raise FileExistsError(f"File download from '{url}' failed : {filepath} does not exist.")


        return filepath
    # Page save