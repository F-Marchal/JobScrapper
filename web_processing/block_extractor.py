import os
import re
import tempfile
import time
import zipfile
from typing import Iterator, Protocol, TypeVar, Generic, Literal


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
from web_processing.web_page_parser import WebPageProcessor

_T = TypeVar("_T") # bound=Hashable
class HTMLBlockExtractor(Protocol):
    def __call__(self, soup: BeautifulSoup) -> BeautifulSoup: ...

class HTMLBlockConvertor(Protocol[_T]):
    def __call__(self, soup: BeautifulSoup) -> list[_T] | Iterator[_T]: ...

class WebBlockExtractor(WebPageProcessor, Generic[_T]):
    def __init__(
            self,
            block_extractor: HTMLBlockExtractor,
            block_convertor: HTMLBlockConvertor[_T],
            *args,
            **kwargs):
        super().__init__(*args, **kwargs)
        self.block_convertor = block_convertor
        self.block_extractor: HTMLBlockExtractor = block_extractor

    def extract_block_across_multiple_pages_using_buttons(
            self,
            w_url: str,

            button_finder: ButtonFinder | dict[str, ByType | int | str],
            prepare_page: PreparePage | None = None,
            wait_after_prepare_page: int = 0.5,
            wait_scroll_to_view_button: int = 0.5,
    ):
        with self.start_browser_on(w_url) as browser:
            self.logger.debug("Start browsing elements in %s", w_url)
            pages = browser.iter_through_pages_using_buttons(
                button_finder=button_finder,
                prepare_page=prepare_page,
                wait_after_prepare_page=wait_after_prepare_page,
                wait_scroll_to_view_button=wait_scroll_to_view_button,
            )

            total = 0
            for i, full_html in enumerate(pages):
                block = self._call_block_extractor(full_html, browser.current_url)
                elements = self._call_block_convertor(block, browser.current_url)

                counter = 0
                for en in self._yield_element(elements):
                    yield en
                    counter += 1
                    self.wait_before_calling(browser.current_url)

                self.logger.debug("%s elements found on page %s (%s)", counter, i, browser.current_url)
                total += counter

            self.logger.debug("%s elements extracted from %s.", total, w_url)

    def extract_block_across_multiple_pages_using_url(
            self,
            w_url: str,
            prepare_page: PreparePage | None = None,
            pre_preparation_wait_time: int = 0.5,
            post_preparation_wait_time: int = 0.5,
            retry: int = 2,
            failed_sleep: int = 5,

    ) -> Iterator[_T]:
        known_block = set()
        page_index = 1
        page_already_reached = False
        no_element_in_last_page = False
        total = 0

        # Offers can be split between multiple pages.
        # An invalid page number load the first page.
        # This loop avoid offer duplication
        self.logger.debug("Starting block extraction from '%s'", w_url)
        while not page_already_reached:
            initial_known_block_count = len(known_block)
            initial_total = total

            # ======== Load and process website page ========
            url = w_url.format(page=page_index)
            new_elements_gen = self.extract_block_on_one_page(
                block_collector=known_block,
                add_block_to_collection=True,
                w_url=url,
                prepare_page=prepare_page,
                pre_preparation_wait_time=pre_preparation_wait_time,
                post_preparation_wait_time=post_preparation_wait_time,
                retry=retry,
                failed_sleep=failed_sleep,
            )
            # We have to use the generator now in
            # order to fill <known_block> for the first
            # kill switch
            new_elements = list(new_elements_gen)
            # ======== Load and process website page ========

            # == Kill switch 1 ==
            if initial_known_block_count == len(known_block):
                # We have done a full loop, lets stop !
                # Remember : Offers are supposed to be split between multiple page
                # and an invalid page number might load the first page.
                page_already_reached = True
                self.logger.debug(
                    "Page %s already reached. Quiting loop.", page_index
                )
                continue
            # == Kill switch 1 ==

            for ne in new_elements:
                total += 1
                yield ne

            # == Kill switch 2 ==
            if initial_total == initial_total:
                self.logger.debug("Page %s (url=%s) does nor contain new elements ! ", page_index, url)
                if no_element_in_last_page:
                    page_already_reached = True
                    self.logger.debug(
                        "Page %s and %s contains no job. Quiting loop.",
                        page_index - 1,
                        page_index,
                    )
                no_element_in_last_page = True
            else:
                no_element_in_last_page = False
            # == Kill switch 2 ==
            page_index += 1

        self.logger.debug("Block extraction from '%s' finished. %s elements found.", w_url, total)

    def extract_block_on_one_page(
            self,
            w_url: str,
            block_collector: set[bs4.BeautifulSoup] | None = None,
            add_block_to_collection: bool=True,
            prepare_page: PreparePage | None = None,
            pre_preparation_wait_time: int = 0.5,
            post_preparation_wait_time: int = 0.5,
            retry: int = 2,
            failed_sleep: int = 5,
    ) -> Iterator[_T]:
        self.logger.debug("Parsing %s.", w_url)

        if block_collector is None:
            block_collector = set()
            add_block_to_collection = False

        full_html = self.extract_html_from(
            url=w_url,
            prepare_page=prepare_page,
            pre_preparation_wait_time=pre_preparation_wait_time,
            post_preparation_wait_time=post_preparation_wait_time,
            retry=retry,
            failed_sleep=failed_sleep,
        )

        html_block = self._call_block_extractor(full_html, w_url)

        if html_block in block_collector:
            self.logger.debug(
                "Block already known. Parsing of %s aborted.", w_url
            )
            return

        if add_block_to_collection:
            block_collector.add(html_block)

        new_elements = self._call_block_convertor(html_block, w_url)
        nb_elements = 0

        for ne in self._yield_element(new_elements):
            nb_elements += 1
            yield ne

        self.logger.debug(
            "%s elements found in %s.", nb_elements, w_url
        )

    def _yield_element(self, new_elements):
        for ne in new_elements:
            try:
                yield ne
            except Exception as e:
                self.logger.fatal(
                    "Catch exception during yielding :"
                    " - problematic object : %s"
                    " - error : %s",
                    ne,
                    e,
                )
                raise

    def _call_block_extractor(self, full_html: bs4.BeautifulSoup, url: str) -> bs4.BeautifulSoup:
        # Let's prepare for a potential `block_extractor` failure.
        try:
            return self.block_extractor(full_html)
        except Exception as e:
            self.logger.fatal(
                "Can not use '%s'.block_extractor (%s) on html soup extracted from '%s'."
                "\n - soup : %s"
                "\n - error : %s",
                self, self.block_extractor, url,
                full_html,
                e
            )
            raise e

    def _call_block_convertor(self, html_block: bs4.BeautifulSoup, url: str) -> list[_T]:
        try:
            return self.block_convertor(html_block)
        except Exception as e:
            self.logger.fatal(
                "Can not use '%s'.block_convertor (%s) on html soup extracted from '%s' "
                "and parsed by '%s'.block_convertor (%s)."
                "\n - soup : %s"
                "\n - error : %s",
                self, self.block_convertor, url,
                self, self.block_extractor,
                html_block,
                e
            )
            raise e
