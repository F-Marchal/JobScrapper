from job_scrapper.scrapper_skeleton.sql_core.wrapper_clause_element import (
    ClauseElementWrapper,
)
from sqlalchemy import and_
from tests.conftest import BaseTest

class TestClauseElementWrapper(BaseTest):
    """
    Test main ClauseElement functions
    """
    def test_main(self):
        """Test main functions of ClauseElement"""
        ow = ClauseElementWrapper(
            op=lambda a, b: and_(a, b),
            help_="test_string",
            symbols=["A", "B", "C"]
        )
        self.screen_var("ow", ow)

        assert str(ow) == "A"
        assert ow.help == "test_string"
        assert ow.run_operator(and_, True, False) == False
        assert ow.run(True, False) == False
        assert ow.run(True, False) == ow.run_operator(and_, True, False)