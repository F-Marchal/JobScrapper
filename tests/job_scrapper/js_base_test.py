import pytest
from tests.conftest import BaseTest
import os
from typing import Type
from job_scrapper.scrapper_skeleton.object_core import ScrapperObjectCore

@pytest.mark.jobScrapper
class JobScrapperBaseTestClass(BaseTest):
    @pytest.fixture(autouse=True)
    def set_workdir(self, _setup_tempdir):
        self.get_scrapper().set_workdir(os.path.join(_setup_tempdir, "JS_TEST"))

    def get_scrapper(self) -> Type[ScrapperObjectCore]:
        """Returns a ScrapperObjectCore subclass. Used in set_workdir fixture"""
        raise NotImplementedError