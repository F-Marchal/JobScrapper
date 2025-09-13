from PyPDF2 import PdfReader
import time
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from urllib.parse import unquote, urlparse
import shutil
import os
from .scrapper_skeleton import JobScrapperSkeleton

class PdfJobBaseScrapper(JobScrapperSkeleton):
    def analyse_job_page(self, save_page: bool = False, **keywords: list[str]):
        if not save_page and not keywords:
            # Nothing to do
            return

        pdf_path = self.download_file(self.url)
        page_content = self.parse_pdf(pdf_path)

        if save_page:
            self.export_pdf(pdf_path)

        if keywords:
            self.search_keywords(page_content, **keywords)

    def export_pdf(self, path: str):
        self.logger.debug("Exporting pfd...")
        folder, name = self._generate_job_file_name("pdf")
        final_path = str(os.path.join(folder, name))
        shutil.copy(path, final_path)

    # --- --- Download files  --- ---
    @classmethod
    def download_file(
            cls, url: str, retry: int = 2, timeout: int = 360
    ) -> str | None:
        """
        Download a file using selenium
        :param str url: An url that point to a file
        :param int retry: Number of time that this action can be retried when
            an error occur
        :param int timeout: How long the download can last
        :return None or str: Path to the downloaded file when the download succeed. None otherise.
        """
        # https://stackoverflow.com/questions/43149534/selenium-webdriver-how-to-download-a-pdf-file-with-python

        download_dir = cls.download_temp_dir.name
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        filename = unquote(filename)  # Avoid encoding errors
        filepath = os.path.join(download_dir, filename)

        cls.logger.debug(
            "Downloading file : %s\ntimeout=%s\tExpected path : %s",
            url,
            timeout,
            filepath,
        )
        driver = webdriver.Chrome(
            options=cls.selenium_download_file_with_chrome_options
        )

        try:
            driver.get(url)
            i = 0
            while not os.path.exists(filepath) and i < timeout:
                time.sleep(1)
                i += 1

        except WebDriverException as exception:
            cls.logger.warning("%s\n%s retry left", exception, retry)
            if retry <= 0:
                cls.logger.error(
                    "Multiple exception during interrogation of %s. \n%s",
                    url,
                    exception,
                )
                return None
            time.sleep(cls.sleep_before_retry_downloading)
            return cls.download_file(url)

        time.sleep(cls.sleep_between_downloading)

        if not os.path.exists(filepath):
            cls.logger.warning("Download failed : %s", filepath)
            return None
        cls.logger.debug("Download completed : %s", filepath)
        return filepath

    @staticmethod
    def parse_pdf(path: str) -> str:
        """Open a pdf in PdfReader"""
        pdf = PdfReader(path)
        output = []
        for pages in pdf.pages:
            output.append(pages.extract_text())

        return "\n\n\n\n".join(output)

    # --- --- Download files  --- ---
