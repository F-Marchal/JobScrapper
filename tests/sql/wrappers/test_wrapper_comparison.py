import os
import re
from datetime import datetime
from typing import Any, Callable

import pytest
from sqlalchemy import Column, and_, select

from job_scrapper.sql import (
    COMPARISON_WRAPPERS,
    STRING_TO_COMPARISON_WRAPPERS,
    ComparisonWrapper,
    to_datetime_ymd_or_ymd_hms,
)
from tests.conftest import BaseTest
from tests.table_for_test_only import StringTable


def ilike_filter(
    items_list: list[str], pattern: str, inverse=False
) -> list[str]:
    """Function that act as an ilike filter. Returns items that match a Patter."""
    regex = ComparisonWrapper.ilike_to_regex(pattern)
    if inverse:
        return [
            item
            for item in items_list
            if not re.search(regex, item, re.IGNORECASE)
        ]
    return [
        item for item in items_list if re.search(regex, item, re.IGNORECASE)
    ]


# pylint: disable=R0801
@pytest.mark.sqlalchemy_wrappers
class TestComparisonWrapper(BaseTest):
    """Class that test ComparisonWrapper's methods"""

    def test_to_datetime(self):
        """Test the to_datetime function"""
        d1 = datetime(2025, 9, 5)
        d1_ref = to_datetime_ymd_or_ymd_hms("2025-09-05")
        self.screen_var("d1", d1)
        self.screen_var("d1_ref", d1_ref)
        assert d1 == d1_ref

        d2_ref = datetime(2025, 9, 5, 12, 45, 0)
        d2 = to_datetime_ymd_or_ymd_hms("2025-09-05 12:45:00")
        self.screen_var("d2", d2)
        self.screen_var("d2_ref", d2_ref)
        assert d2 == d2_ref

    @pytest.mark.parametrize(
        "input_str, expected",
        [
            ("5", 5),
            ("5.5", 5.5),
            ("2025-09-05", datetime(2025, 9, 5)),
            ("2025-09-05 12:45:00", datetime(2025, 9, 5, 12, 45, 0)),
        ],
    )
    def test_cast(self, input_str, expected):
        """Test cast function"""
        cw = ComparisonWrapper(
            op=and_,
            help_="Test cw",
            symbols=["TEST"],
            types=[int, float, to_datetime_ymd_or_ymd_hms],
        )
        self.screen_var("Test_cw", cw)
        self.screen_var("Input", input_str)
        self.screen_var("Expected", expected)
        cast = cw.cast(input_str)
        self.screen_var("Cast", cast)

        assert cast == expected

    @pytest.mark.parametrize(
        "input_str, expected, constraint",
        [
            ("5", "5", None),
            ("5.5", 5.5, [float]),
            ("5", 5, [int]),
        ],
    )
    def test_cast_constraint(self, input_str, expected, constraint):
        """Test cast function"""
        cw = ComparisonWrapper(
            op=and_,
            help_="Test cw",
            symbols=["TEST"],
            types=[str, int, float, to_datetime_ymd_or_ymd_hms],
        )
        self.screen_var("Test_cw", cw)
        self.screen_var("Input", input_str)
        self.screen_var("Expected", expected)
        self.screen_var("Constraint", constraint)
        cast = cw.cast(input_str, constraint)
        self.screen_var("Cast", cast)

        assert cast == expected


    def test_cast_failed(self):
        """Test cast function"""
        cw = ComparisonWrapper(
            op=and_,
            help_="Test cw",
            symbols=["TEST"],
            types=[str, int, float, to_datetime_ymd_or_ymd_hms],
        )
        self.screen_var("Test_cw", cw)

        # No error expected
        cw.cast("2025-09-05 12:45:00", [str])
        cw.cast("2025-09-05 12:45:00", [to_datetime_ymd_or_ymd_hms])

        # Error expected
        with pytest.raises(ValueError):
            cw.cast("2025-09-05 12:45:00", [float])
            cw.cast("2025-09-05 12:45:00", [int])

    def test_string_to_comparison_ope(self):
        """Test content of STRING_TO_COMPARISON_WRAPPERS"""
        for key, wrapper in STRING_TO_COMPARISON_WRAPPERS.items():
            self.screen_var("_".join(wrapper.symbols), wrapper)
            assert key in wrapper.symbols
            assert isinstance(wrapper, ComparisonWrapper)

    def test_comparisons_wrappers(self):
        """Ensure that there is no conflict between each wrapper's symbols"""
        self.screen_var("All", STRING_TO_COMPARISON_WRAPPERS)
        for wrapper in COMPARISON_WRAPPERS:
            for s in wrapper.symbols:
                self.screen_var("Wrapper_" + s, wrapper)
                assert STRING_TO_COMPARISON_WRAPPERS[s] == wrapper

    def test_ilike_to_regex(self):
        """Test ilike_to_regex method"""
        assert ComparisonWrapper.ilike_to_regex("%A") == "^.*A$"
        assert ComparisonWrapper.ilike_to_regex("A%") == "^A.*$"
        assert ComparisonWrapper.ilike_to_regex("A") == "^A$"

    def test_ensure_all_operand_are_tested(self):
        """Ensure that all operand defined in STRING_TO_COMPARISON_WRAPPERS are
        tested at least once"""
        tested_op = set()
        expected_op = set(STRING_TO_COMPARISON_WRAPPERS.keys())

        for vals in self.test_operands_simple_parameters:
            tested_op.add(vals[1])

        for vals in self.test_operands_complex_parameters:
            tested_op.add(vals[1])

        self.screen_var("Tested", tested_op)
        self.screen_var("Expected", tested_op)
        tested_but_unknown = tested_op - expected_op
        untested = expected_op - tested_op

        self.screen_var("untested", untested)
        self.screen_var("tested_but_unknown", tested_but_unknown)

        assert len(untested) == 0
        assert len(tested_but_unknown) == 0

    test_operands_simple_parameters = [  # IA Generated
        # ====== INT ======
        (5, "==", 5, lambda a, b: a == b),
        (5, "==", 3, lambda a, b: a == b),  # False
        (5, "!=", 3, lambda a, b: a != b),
        (5, "!=", 5, lambda a, b: a != b),  # False
        (5, ">", 3, lambda a, b: a > b),
        (3, ">", 5, lambda a, b: a > b),  # False
        (3, ">=", 3, lambda a, b: a >= b),
        (2, ">=", 3, lambda a, b: a >= b),  # False
        (2, "<", 5, lambda a, b: a < b),
        (5, "<", 2, lambda a, b: a < b),  # False
        (5, "<=", 5, lambda a, b: a <= b),
        (6, "<=", 5, lambda a, b: a <= b),  # False
        # ====== FLOAT ======
        (5.0, "==", 5.0, lambda a, b: a == b),
        (5.0, "==", 3.0, lambda a, b: a == b),  # False
        (5.0, "!=", 3.0, lambda a, b: a != b),
        (5.0, "!=", 5.0, lambda a, b: a != b),  # False
        (5.5, ">", 3.3, lambda a, b: a > b),
        (3.3, ">", 5.5, lambda a, b: a > b),  # False
        (3.3, ">=", 3.3, lambda a, b: a >= b),
        (2.2, ">=", 3.3, lambda a, b: a >= b),  # False
        (2.2, "<", 5.5, lambda a, b: a < b),
        (5.5, "<", 2.2, lambda a, b: a < b),  # False
        (5.5, "<=", 5.5, lambda a, b: a <= b),
        (6.6, "<=", 5.5, lambda a, b: a <= b),  # False
        # ====== STR ======
        ("abc", "==", "abc", lambda a, b: a == b),
        ("abc", "==", "def", lambda a, b: a == b),  # False
        ("abc", "!=", "def", lambda a, b: a != b),
        ("abc", "!=", "abc", lambda a, b: a != b),  # False
        ("def", ">", "abc", lambda a, b: a > b),
        ("abc", ">", "def", lambda a, b: a > b),  # False
        ("abc", ">=", "abc", lambda a, b: a >= b),
        ("abc", ">=", "def", lambda a, b: a >= b),  # False
        ("abc", "<", "def", lambda a, b: a < b),
        ("def", "<", "abc", lambda a, b: a < b),  # False
        ("abc", "<=", "abc", lambda a, b: a <= b),
        ("def", "<=", "abc", lambda a, b: a <= b),  # False
        # ====== DATETIME ======
        (
            datetime(2025, 1, 1),
            "==",
            datetime(2025, 1, 1),
            lambda a, b: a == b,
        ),
        (
            datetime(2025, 1, 1),
            "==",
            datetime(2024, 12, 31),
            lambda a, b: a == b,
        ),  # False
        (
            datetime(2025, 1, 1),
            "!=",
            datetime(2024, 12, 31),
            lambda a, b: a != b,
        ),
        (
            datetime(2025, 1, 1),
            "!=",
            datetime(2025, 1, 1),
            lambda a, b: a != b,
        ),  # False
        (
            datetime(2025, 1, 2),
            ">",
            datetime(2025, 1, 1),
            lambda a, b: a > b,
        ),
        (
            datetime(2025, 1, 1),
            ">",
            datetime(2025, 1, 2),
            lambda a, b: a > b,
        ),  # False
        (
            datetime(2025, 1, 1),
            ">=",
            datetime(2025, 1, 1),
            lambda a, b: a >= b,
        ),
        (
            datetime(2024, 12, 31),
            ">=",
            datetime(2025, 1, 1),
            lambda a, b: a >= b,
        ),  # False
        (
            datetime(2024, 12, 31),
            "<",
            datetime(2025, 1, 1),
            lambda a, b: a < b,
        ),
        (
            datetime(2025, 1, 1),
            "<",
            datetime(2024, 12, 31),
            lambda a, b: a < b,
        ),  # False
        (
            datetime(2025, 1, 1),
            "<=",
            datetime(2025, 1, 1),
            lambda a, b: a <= b,
        ),
        (
            datetime(2025, 1, 2),
            "<=",
            datetime(2025, 1, 1),
            lambda a, b: a <= b,
        ),  # False
    ]

    @pytest.mark.parametrize(
        "val1, operand, val2, true_operand", test_operands_simple_parameters
    )
    def test_simple_operands(
        self,
        val1: Any,
        operand: str,
        val2: Any,
        true_operand: Callable[[Any, Any], bool],
    ):
        """
        Test each operand defined in STRING_TO_COMPARISON_WRAPPERS
        :param val1: Any value
        :param operand: an operand (string : '==', '<'...)
        :param val2: Any value
        :param true_operand: A
        :return:
        """
        self.screen_var("va1", val1)
        self.screen_var("va2", val2)
        self.screen_var("operand", operand)
        self.screen_var("true_operand", true_operand)
        result = true_operand(val1, val2)
        self.screen_var("Expected", result)
        self.screen_var("ALL", STRING_TO_COMPARISON_WRAPPERS)

        assert operand in STRING_TO_COMPARISON_WRAPPERS
        wrapper = STRING_TO_COMPARISON_WRAPPERS[operand]
        self.screen_var("Wrapper", wrapper)
        w_result = wrapper.run(val1, val2)
        self.screen_var("Wrapper Result", w_result)

        assert w_result == result

    # pylint: disable=W0108
    test_operands_complex_parameters = [  # IA Generated
        # ====== STRING Only ======
        (
            StringTable.name,
            "<-",
            "%lo%",
            lambda entries, pat: ilike_filter(entries, pat),
        ),
        (
            StringTable.name,
            "<-",
            "%bye%",
            lambda entries, pat: ilike_filter(entries, pat),
        ),
        (
            StringTable.name,
            "Contains",
            "%foo%",
            lambda entries, pat: ilike_filter(entries, pat),
        ),
        (
            StringTable.name,
            "Contains",
            "%world",
            lambda entries, pat: ilike_filter(entries, pat),
        ),
        (
            StringTable.name,
            "x-",
            "%bye%",
            lambda entries, pat: ilike_filter(entries, pat, True),
        ),
        (
            StringTable.name,
            "x-",
            "%lo%",
            lambda entries, pat: ilike_filter(entries, pat, True),
        ),
        (
            StringTable.name,
            "~Contains",
            "%world",
            lambda entries, pat: ilike_filter(entries, pat, True),
        ),
        (
            StringTable.name,
            "~Contains",
            "%foo%",
            lambda entries, pat: ilike_filter(entries, pat, True),
        ),
    ]

    @pytest.mark.parametrize(
        "column, operand, val2, true_operand", test_operands_complex_parameters
    )
    def test_complex_operands(
        self,
        column: Column,
        operand: str,
        val2: Any,
        true_operand: Callable[[Any, Any], list],
    ):
        """Test 'complex' operand  stored in STRING_TO_COMPARISON_WRAPPERS"""
        self.screen_var("va1", column)
        self.screen_var("va2", val2)
        self.screen_var("operand", operand)
        self.screen_var("ALL", STRING_TO_COMPARISON_WRAPPERS)

        assert operand in STRING_TO_COMPARISON_WRAPPERS
        wrapper = STRING_TO_COMPARISON_WRAPPERS[operand]
        self.screen_var("Wrapper", wrapper)

        with StringTable.get_session(
            os.path.join(self.test_folder, "test_database.db")
        ) as session:
            all_names = session.execute(select(column)).scalars().all()
            self.screen_var("All_names", all_names)
            result = (
                session.execute(select(column).where(wrapper(column, val2)))
                .scalars()
                .all()
            )
            expected = true_operand(all_names, val2)

        self.screen_var("result", result)
        self.screen_var("expected", expected)

        assert result == expected
