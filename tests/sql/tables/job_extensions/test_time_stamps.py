import datetime

import pytest

from job_scrapper.sql.tables.job_extensions.time_stamps import TimeStamps

from .abstract_job_extra_base import TestJobExtraBase


@pytest.mark.js_tables
class TestTimeStamps(TestJobExtraBase):
    """Ensure that TimeStamps table works as intended"""

    __tested_class__ = TimeStamps
    job_entry_name = "timestamps_entries"
    db_comp1 = {"label": "download", "time_stamp": datetime.datetime.now()}
    db_comp2 = {"label": "upload", "time_stamp": datetime.datetime.now()}
    db_comp3 = {"label": "download", "time_stamp": datetime.datetime.now()}
