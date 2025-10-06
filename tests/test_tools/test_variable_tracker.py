from tests.conftest import BaseTest
import pytest

class TestLogFile(BaseTest):
    """Test LogFile using the BaseTest.logs' LogFile. (As the uniq purpose
    of LogFile is to be used through)"""
    @pytest.mark.parametrize(
        "value, expected", [
            ("Hello", "TEST"),  # Test avec un string
            (42, "42"),  # Test avec un int
            (19.76514, "19.76514"),  # Test avec un int
            (False, "False"),  # Test avec un bool
            (None, "None"),  # Test avec un bool
        ]
    )
    def test_log_basic_type(self, value, expected):
        name = f"Test-{type(value)}"
        self.logs.screen(name, value)
        content = "\n".join(self.logs.get_content())
        # Name
        assert self.contains_pattern(content, rf"'name'.*:.*{name}")
        #
        assert self.contains_pattern(content, expected)
        assert self.contains_pattern(content, expected)
        assert False



