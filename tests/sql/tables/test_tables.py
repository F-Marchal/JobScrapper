import os.path

from sql.tables import BaseTableForJobScrapper, Jobs, Keywords, TimeStamps, Distances, Metadata
from tests.conftest import BaseTest
from datetime import datetime, timedelta

def make_small_database():
    job1 = Jobs(
        contract="Full-time",
        field="Software Engineering",
        localisation="Berlin, Germany",
        origin="LinkedIn",
        title="Backend Developer (Python)",
        url="https://linkedin.com/jobs/backend-developer-berlin-001"
    )

    job2 = Jobs(
        contract="Part-time",
        field="Data Science",
        localisation="Toronto, Canada",
        origin="Indeed",
        title="Junior Data Analyst",
        url="https://indeed.com/job/junior-data-analyst-toronto-002"
    )

    job3 = Jobs(
        contract="Internship",
        field="Marketing",
        localisation="Paris, France",
        origin="Glassdoor",
        title="Digital Marketing Intern",
        url="https://glassdoor.com/job/digital-marketing-intern-paris-003"
    )

    job4 = Jobs(
        contract="Contract",
        field="Cybersecurity",
        localisation="Remote",
        origin="Company Website",
        title="Security Consultant (6 months)",
        url="https://company.com/jobs/security-consultant-004"
    )

    job_keywords = [
        # Job 1
        Keywords(url=job1.url, keyword="Python", occurrence=0),
        Keywords(url=job1.url, keyword="API", occurrence=8),
        Keywords(url=job1.url, keyword="Backend", occurrence=-1),
        Keywords(url=job1.url, keyword="SQL", occurrence=6),

        # Job 2
        Keywords(url=job2.url, keyword="Python", occurrence=20),
        Keywords(url=job2.url, keyword="Data", occurrence=25),
        Keywords(url=job2.url, keyword="SQL", occurrence=10),

        # Job 3
        Keywords(url=job3.url, keyword="Marketing", occurrence=18),
        Keywords(url=job3.url, keyword="API", occurrence=-1),
        Keywords(url=job3.url, keyword="Content", occurrence=0),
        Keywords(url=job3.url, keyword="Analytics", occurrence=8),

        # Job 4
        Keywords(url=job4.url, keyword="Security", occurrence=22),
        Keywords(url=job4.url, keyword="Python", occurrence=7),
        Keywords(url=job4.url, keyword="Cloud", occurrence=-1)
    ]

    # --- METADATA ---
    job_metadata = [
        # Job 1
        Metadata(url=job1.url, key="experience_level", value="Mid-level"),
        Metadata(url=job1.url, key="employment_type", value="Full-time"),
        Metadata(url=job1.url, key="remote", value="No"),

        # Job 2
        Metadata(url=job2.url, key="experience_level", value="Entry-level"),
        Metadata(url=job2.url, key="employment_type", value="Part-time"),
        Metadata(url=job2.url, key="remote", value="Yes"),
        Metadata(url=job2.url, key="education", value="Bachelor’s Degree"),

        # Job 3
        Metadata(url=job3.url, key="experience_level", value="Internship"),
        Metadata(url=job3.url, key="department", value="Marketing"),
        Metadata(url=job3.url, key="remote", value="Hybrid"),

        # Job 4
        Metadata(url=job4.url, key="experience_level", value="Senior"),
        Metadata(url=job4.url, key="contract_duration", value="6 months"),
        Metadata(url=job4.url, key="remote", value="Yes"),
        Metadata(url=job4.url, key="clearance", value="Required")
    ]

    # --- TIMESTAMPS ---
    now = datetime.now()
    job_timestamps = [
        # Job 1
        TimeStamps(url=job1.url, label="posted", time_stamp=now - timedelta(days=10)),
        TimeStamps(url=job1.url, label="updated", time_stamp=now - timedelta(days=5)),

        # Job 2
        TimeStamps(url=job2.url, label="posted", time_stamp=now - timedelta(days=7)),
        TimeStamps(url=job2.url, label="updated", time_stamp=now - timedelta(days=3)),

        # Job 3
        TimeStamps(url=job3.url, label="posted", time_stamp=now - timedelta(days=3)),
        TimeStamps(url=job3.url, label="reviewed", time_stamp=now - timedelta(days=1)),

        # Job 4
        TimeStamps(url=job4.url, label="posted", time_stamp=now - timedelta(days=15)),
        TimeStamps(url=job4.url, label="closed", time_stamp=now - timedelta(days=2)),
        TimeStamps(url=job4.url, label="updated", time_stamp=now - timedelta(days=1))
    ]

    return [job1, job2, job3, job4, *job_keywords, *job_metadata, *job_timestamps]



class TestTableForJobScrapper(BaseTest):
    def test_create_all(self):
        # Database creation :
        db1 = f"{self.test_folder}/database1.db"
        db2 = f"{self.test_folder}/database2.db"
        assert not os.path.exists(db1)
        assert not os.path.exists(db2)

        with BaseTableForJobScrapper.get_session(db1):
            pass

        with BaseTableForJobScrapper.get_session(db2):
            pass

        assert os.path.exists(db1)
        assert os.path.exists(db2)

        assert db1 in BaseTableForJobScrapper.get_known_databases()
        assert db2 in BaseTableForJobScrapper.get_known_databases()

    def test_sanitise_and_commit(self):
        db1 = f"{self.test_folder}/database1.db"
        from job_scrapper.scrapper_skeleton.object_core import CoreLogger

        with BaseTableForJobScrapper.get_session(db1, logger=CoreLogger.logger) as session:
            session.add_all(make_small_database())

        assert False


