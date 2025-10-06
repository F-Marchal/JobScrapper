import pytest
from tests.conftest import BaseTest

from job_scrapper.scrapper_skeleton.logger_core import (
    CoreLogger,
)


@pytest.mark.logs
class TestCoreLogger(BaseTest):
    """Test CoreLogger main functionalities."""

    @pytest.fixture
    def cl(self):
        """Give a fresh CoreLogger class to test methods as 'cl'"""
        return self.get_fresh_class(CoreLogger)

    def test_file_logging_level(self, cl: CoreLogger):
        """Test that loggings levels management works as intended"""
        # Generate test content
        cl.set_logging_level("CRITICAL")
        self.screen_var("CoreLogger", cl)

        assert cl.start_file_logging("process.logs", level="WARNING")
        cl.logger.debug("(Test log)")
        cl.logger.warning("(Test log)")
        cl.logger.error("(Test log)")

        # Load content
        with open("process.logs", "r", encoding="UTF-8") as f:
            lines = "".join(f.readlines())

        # Tests
        assert not self.contains_pattern("DEBUG", lines)
        assert self.contains_pattern("WARNING", lines)
        assert self.contains_pattern("ERROR", lines)

    def test_start_stop_file_logging(self, cl: CoreLogger):
        """Test <start_file_logging> and <stop_file_logging>"""
        cl.set_logging_level("CRITICAL")
        self.screen_var("CoreLogger", cl)

        # Log in first file
        assert cl.start_file_logging("process1.logs", level="DEBUG")
        cl.logger.warning("(Test log)")
        self.re_screen_all()

        # Stop logging
        cl.stop_file_logging()
        self.re_screen_all()

        # Log in second file
        assert cl.start_file_logging("process2.logs", level="WARNING")
        cl.logger.error("(Test log)")
        self.re_screen_all()

        # Read files
        with open("process1.logs", "r", encoding="UTF-8") as f:
            lines_from_file1 = "".join(f.readlines())

        with open("process2.logs", "r", encoding="UTF-8") as f:
            lines_from_file2 = "".join(f.readlines())

        # Asserts
        assert self.contains_pattern("WARNING", lines_from_file1)
        assert not self.contains_pattern("ERROR", lines_from_file1)

        assert not self.contains_pattern("WARNING", lines_from_file2)
        assert self.contains_pattern("ERROR", lines_from_file2)

    def test_redirect_logs_to_file(self, cl: CoreLogger):
        """Test <cl.redirect_logs_to_file>"""
        cl.set_logging_level("CRITICAL")
        self.screen_var("CoreLogger", cl)

        # Generate test content
        with open("process.logs", "w", encoding="UTF-8") as file:
            with cl.redirect_logs_to_file(file, level="WARNING"):
                cl.logger.debug("(Test log)")
                cl.logger.warning("(Test log)")
                cl.logger.error("(Test log)")

        # Load content
        with open("process.logs", "r", encoding="UTF-8") as f:
            lines = "".join(f.readlines())

        # Tests
        assert not self.contains_pattern("DEBUG", lines)
        assert self.contains_pattern("WARNING", lines)
        assert self.contains_pattern("ERROR", lines)
