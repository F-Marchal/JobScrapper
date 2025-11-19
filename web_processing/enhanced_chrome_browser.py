import os
import re
import tempfile
import time
import zipfile
from typing import Callable, Any, Iterator, Protocol
from urllib.parse import urlparse

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


class ButtonFinder(Protocol):
    def __call__(self, driver: "EnhancedChrome") -> WebElement | None: ...


class PreparePage(Protocol):
    def __call__(self, driver: "EnhancedChrome") -> None: ...


class EnhancedChrome(webdriver.Chrome, SecondaryLoggerUser):
    def __init__(
            self,
            *args,
            logger: logging.Logger | None,
            **kwargs,
    ):
        super().__init__(*args, **kwargs)
        SecondaryLoggerUser.__init__(self, logger)

    def scroll_down(self) -> None:
        self.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )

    def scroll_to_view(self, element: WebElement) -> None:
        self.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", element
        )

    def close_pop_up(
            self,
            by: ByType,
            button_identifier: str,
            timeout: int = 15,

    ):
        try:
            pop_up = self.wait_until_clickable(by, button_identifier, timeout)
            pop_up.click()
        except TimeoutException as te:
            raise WebDriverException(
                f"Unable to find targeted popup in time ({timeout}sec) : '{button_identifier}' ({by}). ({te})"
            )

    def safe_close_pop_up(
            self,
            *args,
            **kwargs,
    ):
        try:
            return self.close_pop_up(*args, **kwargs)
        except TimeoutException as te:
            self.logger.debug("Exception catch by safe_close_pop_up : %s", te)

    def wait_until_clickable(
            self,
            selector: ByType,
            element: str,
            timeout: int = 15,
    ):
        self.logger.debug(
            "Waiting %s seconds in order to find '%s' (%s). url=%s",
            timeout, element, selector, self.current_url
        )
        obj = WebDriverWait(self, timeout).until(
            cond.element_to_be_clickable((selector, element))
        )
        return obj

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
            if prepare_page:
                prepare_page(self)
            time.sleep(wait_after_prepare_page)

            yield BeautifulSoup(self.page_source, "html.parser")

            # ---------- Find button state --------------
            self.logger.debug("Seeking 'next' button on page %s using %s", i, button_finder)
            if isinstance(button_finder, dict):
                next_page_btn = self.get_next_page_button(**button_finder)
            else:
                next_page_btn = button_finder(self)
            is_enabled = next_page_btn is not None
            # --------------------------------------------

            # Load next page
            if is_enabled:
                self.logger.debug("'next' button found on page %s : %s ", i, next_page_btn)
                self.scroll_to_view(next_page_btn)
                time.sleep(wait_scroll_to_view_button)
                next_page_btn.click()


            else:
                self.logger.debug("No 'next' button found on page %s ! Quitting page iteration ", i)

            i += 1

    def get_next_page_button(
            self,
            by: ByType,
            button_id: str,
            timeout: int = 15,
    ) -> WebElement | None:
        try:
            next_button = self.wait_until_clickable(
                by, button_id, timeout
            )
            return next_button

        except TimeoutException as te:
            self.logger.debug("Can not find '%s' (%s). %s", button_id, by, te)
            return None
