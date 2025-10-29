from sql.tables.job_extensions.metadata import Metadata
import pytest
from .abstract_job_extra_base import TestJobExtraBase

@pytest.mark.js_tables
class TestMetadata(TestJobExtraBase):
    """Ensure that Metadata table works as intended"""
    __tested_class__ = Metadata
    job_entry_name = "metadata_entries"
    db_comp1 = {
        "key": "education",
        "value": "degree in informatics"
    }
    db_comp2 = {
        "key": "type",
        "value": "CDD"
    }
    db_comp3 = {
        "key": "year of creation",
        "value": "1999"
    }

