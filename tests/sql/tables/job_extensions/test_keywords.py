import pytest

from sql.tables.job_extensions.keywords import Keywords

from .abstract_job_extra_base import TestJobExtraBase


@pytest.mark.js_tables
class TestKeywords(TestJobExtraBase):
    """Ensure that keyword table works as intended"""

    __tested_class__ = Keywords
    job_entry_name = "keywords_entries"
    db_comp1 = {"keyword": "download", "occurrence": 55}
    db_comp2 = {"keyword": "upload", "occurrence": None}
    db_comp3 = {
        "keyword": "download",
    }
