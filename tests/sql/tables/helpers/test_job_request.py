import datetime

import pytest

from job_scrapper.scrapper_skeleton.sql_core import ScrapperSQLightCore
from sql.tables.helpers.job_request import JobRequest, Jobs, Places
from tests.conftest import BaseTest

TSS = ScrapperSQLightCore.time_stamp_suffix
MS = ScrapperSQLightCore.metadata_suffix
KS = ScrapperSQLightCore.keyword_suffix
DS = ScrapperSQLightCore.distance_suffix


class RequestValidator:
    """Ease the definition of pytest.parametrize for test_complex_requests.
    Contains input values required by test_complex_requests."""

    # pylint: disable=R0913,R0917
    def __init__(
        self,
        name: str,
        request_dict: dict[str, list[str]],
        expected_keys: set[str],
        expected_lines: set[tuple],
        unexpected_lines: set[tuple],
    ):
        self.name = name
        self.request_dict = request_dict
        self.expected_keys = expected_keys
        self.expected_lines = expected_lines
        self.unexpected_lines = unexpected_lines

    def __str__(self):
        return self.name


COLUMN_SUBSET_REQUEST = RequestValidator(
    name="COLUMN_SUBSET_REQUEST",
    request_dict={"columns": ["url", "field", "contract"]},
    expected_keys={"url", "field", "contract"},
    expected_lines={
        ("https://ftt.fr", "Marketing", "FREELANCE"),
        ("https://hello-work.fr", "Data science", "CDI"),
        ("https://indeed.fr", "Engineering", "CDD"),
        ("https://linkedin.fr/", "Biology", "CDI"),
    },
    unexpected_lines=set(),
)
URL_TIME_STAMPS = RequestValidator(
    name="URL_TIME_STAMPS",
    request_dict={
        "columns": ["url"],
        "time_stamp": [
            "Check time",
            f"Scraping time{TSS}",
        ],  # Test both with and without suffix
    },
    expected_keys={"url", f"check time{TSS}", f"scraping time{TSS}"},
    expected_lines={
        ("https://ftt.fr", datetime.datetime(2024, 11, 3, 20, 25, 4), None),
        ("https://indeed.fr", None, datetime.datetime(2025, 11, 3, 20, 25, 4)),
        ("https://hello-work.fr", None, None),
        ("https://linkedin.fr/", None, None),
    },
    unexpected_lines=set(),
)
URL_KEYWORDS = RequestValidator(
    name="URL_KEYWORDS",
    request_dict={
        "columns": ["url"],
        "keywords": [
            "Software",
            f"SEO{KS}",
        ],  # Test both with and without suffix
    },
    expected_keys={"url", f"software{KS}", f"seo{KS}"},
    expected_lines={
        ("https://indeed.fr", 120, None),
        ("https://ftt.fr", 47, 72),
        ("https://hello-work.fr", None, None),
        ("https://linkedin.fr/", None, None),
    },
    unexpected_lines=set(),
)
URL_KEYWORDS_ORDERED = RequestValidator(
    name="URL_KEYWORDS",
    request_dict={
        "columns": ["url"],
        "keywords": [
            "Software",
            f"SEO{KS}",
        ],  # Test both with and without suffix
        "order_by": [f"seo{KS}", "url", "software"],
    },
    expected_keys={"url", f"software{KS}", f"seo{KS}"},
    expected_lines={
        (None, "https://hello-work.fr", None),
        (None, "https://linkedin.fr/", None),
        (72, "https://ftt.fr", 47),
        (None, "https://indeed.fr", 120),
    },
    unexpected_lines=set(),
)
URL_METADATA = RequestValidator(
    name="URL_KEYWORDS",
    request_dict={
        "columns": ["url"],
        "metadata": [
            "Message",
            f"Account{MS}",
        ],  # Test both with and without suffix
    },
    expected_keys={"url", f"message{MS}", f"account{MS}"},
    expected_lines={
        ("https://indeed.fr", "Looking_for_talent!", "12_345"),
        ("https://linkedin.fr/", "<3", "9_000"),
        ("https://ftt.fr", "Excited_to_connect!", "5_678"),
        ("https://hello-work.fr", "Innovative_solutions!", "3_200"),
    },
    unexpected_lines=set(),
)
URL_DISTANCES = RequestValidator(
    name="URL_DISTANCES",
    request_dict={
        "columns": ["url"],
        "distances_from": [
            "Nice, France",
            f"Paris, France{DS}",
        ],  # Test both with and without suffix
    },
    expected_keys={"url",  f"Nice, France{DS}",  f"Paris, France{DS}"},
    expected_lines={
        ('https://indeed.fr', 297.579, 392.11),
        ('https://hello-work.fr', 468.077, 588.134),
        ('https://ftt.fr', 685.108, 0.0),
        ('https://linkedin.fr/', 792.038, 112.054)
    },
    unexpected_lines=set(),
)
MASSIVE_REQUEST = RequestValidator(
    name="URL_DISTANCES",
    request_dict={
        "columns": ["url", "field", "contract"],
        "metadata": ["Message", f"Account{MS}"],
        "distances_from": ["Nice, France", f"Paris, France{DS}"],
        "keywords": ["Software", f"SEO{KS}"],
        "order_by": [
            f"seo{KS}",
            "url",
            "software",
            "Message",
        ],
    },
    expected_keys={
        "url",
        "field",
        "contract",
        f"message{MS}",
        f"account{MS}",
        f"software{KS}",
        f"seo{KS}",
        f"Nice, France{DS}",
        f"Paris, France{DS}",
    },
    expected_lines={
        (None, 'https://linkedin.fr/', None, '<3', 'Biology', 'CDI', 792.038, 112.054, '9_000'),
        (None, 'https://indeed.fr', 120, 'Looking_for_talent!', 'Engineering', 'CDD', 297.579, 392.11, '12_345'),
        (72, 'https://ftt.fr', 47, 'Excited_to_connect!', 'Marketing', 'FREELANCE', 685.108, 0.0, '5_678'),
        (None, 'https://hello-work.fr', None, 'Innovative_solutions!', 'Data science', 'CDI', 468.077, 588.134, '3_200')
    },
    unexpected_lines=set(),
)
# TODO: Test with conditions
# TODO: Test with Complex request (A And B) Or C...

@pytest.mark.sqlalchemy_wrappers
class TestJobRequest(BaseTest):
    """Test JobRequest with ScrapperSQLightCore configuration
    as it will mostly be used that way."""

    icl = ScrapperSQLightCore
    icl.set_logging_level("INFO")

    def test_order_by__no_suffix(self):
        """Test JobRequest.order_by in a situation where columns
        possess suffixes"""
        cols = list(Jobs.get_columns_using_sql_name().values())
        names = [Jobs.field.key, Jobs.contract.key, Jobs.localisation.key]
        self.screen_var("cols", cols)
        self.screen_var("names", names)

        jr = self.make_job_requester()
        results = jr.build_request_order_by(cols, names)
        self.screen_var("results", results)

        assert results[0].key == Jobs.field.key
        assert results[1].key == Jobs.contract.key
        assert results[2].key == Jobs.localisation.key

    def test_simplest_request(self):
        """Test one of the simplest call of  JobRequest.build_request"""
        scrappers = {sqlc.url: sqlc for sqlc in self.create_database()}
        requester = ScrapperSQLightCore.get_job_requester()

        with ScrapperSQLightCore.get_maindb_session() as session:
            query = requester.build_request(
                session,
            )
            result = requester.execute_request(session, query)

        expected_keys = set(Jobs.get_columns_using_sql_name())
        assert set(result.keys()) == expected_keys

        objs = {}

        for tup in result.all():
            objs[tup[-1]] = dict(zip(result.keys(), tup))

        # Assert that all urls are found
        assert set(scrappers.keys()) == set(objs.keys())

    @pytest.mark.parametrize(
        "request_validator",
        [
            COLUMN_SUBSET_REQUEST,
            URL_TIME_STAMPS,
            URL_KEYWORDS,
            URL_KEYWORDS_ORDERED,
            URL_METADATA,
            URL_DISTANCES,
            MASSIVE_REQUEST,
        ],
    )
    def test_complex_requests(self, request_validator: RequestValidator):
        """
        Main test body for JobRequest. Test a large amount of possible situation
        """
        self.create_database()
        self.screen_var("request_validator", request_validator)
        requester = ScrapperSQLightCore.get_job_requester()

        with ScrapperSQLightCore.get_maindb_session() as session:
            query = requester.build_request(
                session, **request_validator.request_dict
            )
            result = requester.execute_request(session, query)

        result_set = set(result.all())
        self.screen_var("result keys", set(result.keys()))
        self.screen_var("result_set", result_set)

        assert set(result.keys()) == request_validator.expected_keys
        assert request_validator.expected_lines.issubset(result_set)
        if request_validator.unexpected_lines:
            assert not request_validator.unexpected_lines.issubset(result_set)

    def test_column_name_compatibility(self):
        """
        Ensure that Jobs' columns name are compatible with column_name_normaliser().
        If not we might have conflict during column request.
        There is no need to verify other table since all of them are lookup table
        and column's names will not be passed inside column_name_normaliser().
        (Only values in the 'label' column will.)
        """
        job_requester = self.make_job_requester()

        for col_names in Jobs.get_columns_using_sql_name().keys():
            cleaned_name = job_requester.column_name_normaliser(col_names)
            self.screen_var(f"cleaned_{col_names}", cleaned_name)

            assert col_names == cleaned_name

    #################################
    #           Utils               #
    #################################
    @staticmethod
    def make_job_requester() -> JobRequest:
        """Generate an initialised JobRequest"""
        return ScrapperSQLightCore.get_job_requester()

    def create_database(self):
        """Create a database that can be requested by JobRequest returned by <make_job_requester>"""
        scrapers = []

        ssc1 = ScrapperSQLightCore(
            "https://linkedin.fr/",
            title="data ingenier",
            localisation="Rouen, France",
            contract_type="CDI",
            field="Biology",
        )
        now = datetime.datetime(2025, 11, 3, 20, 25, 4).timetuple()
        ssc1.add_metadata("Message", "<3")
        ssc1.add_metadata("Account :", "9 \t000")
        # ssc1.add_distance_to("Paris, France", 100.678)
        ssc1.add_time_stamps("Test time", now)
        ssc1.add_keyword_count("Informatics", 45)
        scrapers.append(ssc1)

        ssc2 = ScrapperSQLightCore(
            "https://indeed.fr",
            title="Software Engineer",
            localisation="Lyon, France",
            contract_type="CDD",
            field="Engineering",
        )
        now = datetime.datetime(2025, 11, 3, 20, 25, 4).timetuple()
        ssc2.add_metadata("Message", "Looking for talent!")
        ssc2.add_metadata("Account:", "12 \t345")
        # ssc2.add_distance_to("Marseille, France", 300.5)
        ssc2.add_time_stamps("Scraping time", now)
        ssc2.add_keyword_count("Software", 120)
        scrapers.append(ssc2)

        ssc3 = ScrapperSQLightCore(
            "https://ftt.fr",
            title="Digital Marketing Manager",
            localisation="Paris, France",
            contract_type="Freelance",
            field="Marketing",
        )
        now = datetime.datetime(2024, 11, 3, 20, 25, 4).timetuple()
        ssc3.add_metadata("Message", "Excited to connect!")
        ssc3.add_metadata("Account:", "5 \t678")
        # ssc3.add_distance_to("Bordeaux, France", 500.9)
        # ssc3.add_distance_to("Nice, France", 900)
        ssc3.add_time_stamps("Check time", now)
        ssc3.add_keyword_count("SEO", 72)
        ssc3.add_keyword_count("Software", 47)
        scrapers.append(ssc3)

        ssc4 = ScrapperSQLightCore(
            "https://hello-work.fr",
            title="Data Scientist",
            localisation="Toulouse, France",
            contract_type="CDI",
            field="Data Science",
        )
        now = datetime.datetime(2024, 11, 11, 11, 11, 4).timetuple()
        ssc4.add_metadata("Message", "Innovative solutions!")
        ssc4.add_metadata("Account:", "3 \t200")
        # ssc4.add_distance_to("Nice, France", 600.4)
        ssc4.add_time_stamps("Last checked", now)
        ssc4.add_keyword_count("Machine Learning", 89)
        scrapers.append(ssc4)

        self.screen_multiple_vars("ssc", *scrapers)

        nice = Places(
            localisation="Nice, France",
            longitude=7.2620,
            latitude=43.7102
        )
        paris = Places(
            localisation="Paris, France",
            longitude=2.3522,
            latitude=48.8566
        )
        rouen = Places(
            localisation="Rouen, France",
            longitude=1.0993,
            latitude=49.4431
        )
        lyon = Places(
            localisation="Lyon, France",
            longitude=4.8357,
            latitude=45.7578
        )
        toulouse = Places(
            localisation="Toulouse, France",
            longitude=1.4442,
            latitude=43.6047
        )

        self.screen_var("nice", nice)
        self.screen_var("paris", paris)
        self.screen_var("rouen", rouen)
        self.screen_var("lyon", lyon)
        self.screen_var("toulouse", toulouse)

        with ScrapperSQLightCore.get_maindb_session() as session:
            session.add_all((nice, paris, rouen, lyon, toulouse))
        ScrapperSQLightCore.sql_batch_export(*scrapers)

        return scrapers
