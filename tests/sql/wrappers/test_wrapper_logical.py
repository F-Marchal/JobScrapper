from typing import Any, Callable

import pytest

from sql.wrappers.wrapper_logical import (
    LOGICAL_WRAPPERS,
    STRING_TO_LOGICAL_WRAPPERS,
    LogicalWrapper,
)
from tests.conftest import BaseTest


# pylint: disable=R0801
@pytest.mark.sqlalchemy_wrappers
class TestLogicalWrapper(BaseTest):
    """Test LogicalWrapper's methods."""

    def test_string_to_logic_ope(self):
        """Test content of STRING_TO_LOGIC_OPE"""
        for key, wrapper in STRING_TO_LOGICAL_WRAPPERS.items():
            self.screen_var("_".join(wrapper.symbols), wrapper)
            assert key in wrapper.symbols
            assert isinstance(wrapper, LogicalWrapper)

    def test_comparisons_wrappers(self):
        """Ensure that there is no conflict between each wrapper's symbols"""
        self.screen_var("All", STRING_TO_LOGICAL_WRAPPERS)
        for wrapper in LOGICAL_WRAPPERS:
            for s in wrapper.symbols:
                self.screen_var("Wrapper_" + s, wrapper)
                assert STRING_TO_LOGICAL_WRAPPERS[s] == wrapper

    def test_ensure_all_operand_are_tested(self):
        """Ensure that all operand defined in STRING_TO_COMPARISON_WRAPPERS are
        tested at least once"""
        tested_op = set()
        expected_op = set(STRING_TO_LOGICAL_WRAPPERS.keys())

        for vals in self.test_logical_parameters:
            tested_op.add(vals[1])

        self.screen_var("Tested", tested_op)
        self.screen_var("Expected", tested_op)
        tested_but_unknown = tested_op - expected_op
        untested = expected_op - tested_op

        self.screen_var("untested", untested)
        self.screen_var("tested_but_unknown", tested_but_unknown)

        assert len(untested) == 0
        assert len(tested_but_unknown) == 0

    test_logical_parameters = [
        # ====== OR variants ======
        (True, "|", False, lambda a, b: a or b),
        (False, "|", False, lambda a, b: a or b),  # False
        (True, "Or", False, lambda a, b: a or b),
        (False, "Or", False, lambda a, b: a or b),  # False
        # ====== OR NOT variants ======
        (True, "|~", False, lambda a, b: a or not b),
        (False, "|~", True, lambda a, b: a or not b),  # False
        (True, "Or not", False, lambda a, b: a or not b),
        (False, "Or not", True, lambda a, b: a or not b),  # False
        # ====== AND variants ======
        (True, "&", True, lambda a, b: a and b),
        (True, "&", False, lambda a, b: a and b),  # False
        (True, "And", True, lambda a, b: a and b),
        (False, "And", True, lambda a, b: a and b),  # False
        # ====== AND NOT variants ======
        (True, "&~", False, lambda a, b: a and not b),
        (True, "&~", True, lambda a, b: a and not b),  # False
        (True, "And not", False, lambda a, b: a and not b),
        (False, "And not", False, lambda a, b: a and not b),  # False
        # ====== XOR variants ======
        (True, "^", False, lambda a, b: a ^ b),
        (True, "^", True, lambda a, b: a ^ b),  # False
        (True, "Xor", False, lambda a, b: a ^ b),
        (False, "Xor", False, lambda a, b: a ^ b),  # False
    ]

    @pytest.mark.parametrize(  # IA Generated
        "val1, operand, val2, true_operand", test_logical_parameters
    )
    def test_simple_operands(
        self,
        val1: Any,
        operand: str,
        val2: Any,
        true_operand: Callable[[bool, bool], bool],
    ):
        """
        Test each operand defined in STRING_TO_LOGICAL_WRAPPERS
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
        self.screen_var("ALL", STRING_TO_LOGICAL_WRAPPERS)

        assert operand in STRING_TO_LOGICAL_WRAPPERS
        wrapper = STRING_TO_LOGICAL_WRAPPERS[operand]
        self.screen_var("Wrapper", wrapper)
        w_result = wrapper.run(val1, val2)
        self.screen_var("Wrapper Result", w_result)

        assert w_result == result
