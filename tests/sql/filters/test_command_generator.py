from sql.filters.filter_generator import FilterGenerator
from sql.filters.filter_part import FilterPart
from sql.tables.jobs import Jobs
from tests.conftest import BaseTest
import pytest
from sqlalchemy.sql import operators as ope
from sqlalchemy import and_
from tools.logger_core import CoreLogger
from sqlalchemy.sql.elements import ClauseElement

#####################################
#                UTILS              #
#####################################
def quick_filter(string: str) -> FilterPart:
    """Returns kwargs used by (almost) all FilterPart during tests."""
    kw = {
        "string_to_columns": Jobs.get_columns_using_sql_name(),
        "string_formater": lambda s: s.lower(),
        "logger": CoreLogger.logger
    }
    return FilterPart(string, **kw)


@pytest.mark.sql_filters
class TestFilterGenerator(BaseTest):
    """Ensure that FilterGenerator correctly generate filters from a list of FilterPart"""

    @pytest.mark.parametrize(
        "filter_, expected",
        [
            (and_(ope.eq(Jobs.url, "https://google.fr"), ope.eq(Jobs.contract, "CDD")),
             "jobs.url = 'https://google.fr' AND jobs.contract = 'CDD'"),
        ]
    )
    def test_clause_element_to_string(self, filter_: ClauseElement, expected: str):
        """Ensure that clause_element_to_string returns the correct string attached to an expression"""
        assert FilterGenerator.clause_element_to_string(filter_) == expected

    @pytest.mark.parametrize(
        "fp, expected",
        [
            ([quick_filter("url::>=::5")], "jobs.url >= 5"),
            ([quick_filter("url::==::5"), quick_filter("contract::==::5")], "jobs.url = 5 AND jobs.contract = 5"),
            ([quick_filter("url::==::5"), quick_filter("|::contract::==::5")], "jobs.url = 5 OR jobs.contract = 5"),
            ([quick_filter("url::==::5"), quick_filter("|~::contract::==::5")], "jobs.url = 5 OR jobs.contract != 5"),
            ([quick_filter("(::::url::>=::5")], "jobs.url >= 5"),

            # We can end with ')'
            ([quick_filter("|::contract::>=::5"), quick_filter("(::::url::>=::5"), quick_filter(")::|::field::>=::5")],
            "jobs.contract >= 5 AND (jobs.url >= 5 OR jobs.field >= 5)"),

            # Ensure that we can start with a '('
            ([quick_filter("(::::url::>=::5"), quick_filter(")::::field::>=::5"), quick_filter("|::contract::>=::5")],
             "jobs.url >= 5 AND jobs.field >= 5 OR jobs.contract >= 5"),
            ([quick_filter("(::|::url::>=::5"),
              quick_filter(")::|::contract::>=::5"),
              quick_filter(")(::&::field::>=::5"),
              quick_filter(")::|::contract::>=::15")
              ], "(jobs.url >= 5 OR jobs.contract >= 5) AND (jobs.field >= 5 OR jobs.contract >= 15)"),

            # With reverse conditions
            ([quick_filter("url::==::5"), quick_filter("&~::contract::==::5")], "jobs.url = 5 AND jobs.contract != 5"),
            ([quick_filter("url::==::5"), quick_filter("|~::contract::>::5")], "jobs.url = 5 OR jobs.contract <= 5"),
        ]
    )
    def test_valid_command(self, fp: list[FilterPart], expected: str):
        """Try to generate a filter from a list of FilterPart"""
        self.screen_multiple_vars("fp", *fp)

        fg = FilterGenerator(fp)
        self.screen_var('fg', fg)

        assert str(fg) == expected


