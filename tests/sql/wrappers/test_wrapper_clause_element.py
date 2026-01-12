from sqlalchemy import and_
import pytest
from job_scrapper.sql import (
    ClauseElementWrapper,
)
from tests.conftest import BaseTest

@pytest.mark.sqlalchemy_wrappers
class TestClauseElementWrapper(BaseTest):
    """
    Test main ClauseElement functions
    """

    def test_main(self):
        """Test main functions of ClauseElement"""
        # pylint: disable=W0108
        ow = ClauseElementWrapper(
            op=lambda a, b: and_(a, b),
            help_="test_string",
            symbols=["A", "B", "C"],
        )
        self.screen_var("ow", ow)

        assert str(ow) == "A"
        assert ow.help == "test_string"
        assert ow.run_operator(and_, True, False) is False
        assert ow.run(True, False) is False
        assert ow.run(True, False) == ow.run_operator(and_, True, False)
