from job_scrapper.scrapper_skeleton.sql_core.condition_wrapper import (
    STRING_TO_COMPARISON_OPE,
    STRING_TO_LOGIC_OPE,
    to_datetime,
    ConditionWrapper
)
from datetime import datetime
from tests.conftest import BaseTest
import pytest

class TestConditionWrapper(BaseTest):
    """
    Test main ConditionWrapper components.
    DOES NOT TEST ConditionWrapper OPERATOR COMPATIBILITY WITH SESSION.QUERY.FILTER()
    """
    def test_string_to_comparison_ope(self):
        """Test content of STRING_TO_COMPARISON_OPE"""
        for key, wrapper in STRING_TO_COMPARISON_OPE.items():
            self.screen_var(wrapper.symbol, wrapper)
            assert key == wrapper.symbol

    def test_string_to_logic_ope(self):
        """Test content of STRING_TO_LOGIC_OPE"""
        for key, wrapper in STRING_TO_LOGIC_OPE.items():
            self.screen_var(wrapper.symbol, wrapper)
            assert key == wrapper.symbol

    def test_to_datetime(self):
        d1 = datetime(2025, 9, 5)
        d1_ref = to_datetime("2025-09-05")
        self.screen_var("d1", d1)
        self.screen_var("d1_ref", d1_ref)
        assert d1 == d1_ref

        d2_ref =  datetime(2025, 9, 5, 12, 45, 0)
        d2 = to_datetime("2025-09-05 12:45:00")
        self.screen_var("d2", d2)
        self.screen_var("d2_ref", d2_ref)
        assert d2 == d2_ref

    @pytest.mark.parametrize(
        "input_str, expected",
        [
            ("5", 5),
            ("5.5", 5.5),
            ("2025-09-05",  datetime(2025, 9, 5)),
            ("2025-09-05 12:45:00",  datetime(2025, 9, 5, 12, 45, 0)),
        ],
    )
    def test_cast(self, input_str, expected):
        """Test cast function"""
        cw = ConditionWrapper(
            op=lambda *args: True,
            help_="Test cw",
            symbol="TEST",
            types=[int, float, to_datetime]
        )
        self.screen_var("Test_cw", cw)
        self.screen_var("Input", input_str)
        self.screen_var("Expected", expected)
        cast = cw.cast(input_str)
        self.screen_var("Cast", cast)

        assert cast == expected
