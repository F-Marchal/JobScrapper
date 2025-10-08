import datetime
import os
import re
import shutil
import types
import typing
from inspect import getfile

import pytest

from .test_tools.variable_tracker import VariableTracker


def pytest_addoption(parser):
    """Add --keep-test-dir option to keep  test folder even when they succeed"""
    parser.addoption(
        "--keep-test-dir",
        action="store_true",
        default=False,
        help="Keep test folder even when they succeed.",
    )


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
# pylint: disable=W0613
# Even if not used, call is mandatory and can not be replaced by _
def pytest_runtest_makereport(item, call):
    """New hook. Used in order to generate a rep_call.failed"""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)
    return rep


class BaseTest:
    """
    Base class for unittest.
    When a test run a ./.tests/<class name>-<test name>-<start date> folder is generated.
    This folder is deleted when test succeed (unless pytest was run with --keep-test-dir) and kept when test failed.
    In this folder a tests.tracker file is generated through a VariableTracker.
    This VariableTracker allows var screening.

    In addition, a number of tool method are contained inside this class.
    """

    @property
    def get_test_folder_parent(self) -> str:
        """Return path that lead to a .test/ folder next to the file that define
        this class"""
        folder = os.path.dirname(getfile(self.__class__))
        abs_folder = os.path.abspath(folder)
        return os.path.join(abs_folder, ".tests/")

    @pytest.fixture(autouse=True)
    # pylint: disable=W0201
    # I can not define this attributes in an __init__ !
    # (I tried, and it failed miserably : All test are viewed as "Empty suite")
    def _setup_tempdir(self, request):
        """Set up a temporary directory work dir in <get_test_folder_parent>.
        This work dir is named with <Class name>-<test name>-<time stamp>
        This directory is kept if failed or `--keep-test-dir`. Otherwise,
        this folder is deleted."""

        # ---- Generate test dir names ----
        test_name = request.node.name
        start_date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        test_dir_name_in_progress = (
            f"IN_PROGRESS-{type(self).__name__}-{test_name}-{start_date}"
        )
        test_dir_name_succeed = (
            f"SUCCEED-{type(self).__name__}-{test_name}-{start_date}"
        )
        test_dir_name_failed = (
            f"FAILED-{type(self).__name__}-{test_name}-{start_date}"
        )

        # ---- Generate folder ----
        test_abs_parent_folder = self.get_test_folder_parent
        self.test_folder = os.path.join(
            test_abs_parent_folder, test_dir_name_in_progress
        )
        os.makedirs(self.test_folder, exist_ok=True)
        os.chdir(self.test_folder)

        # ---- Generate logs ----
        self.tracker = VariableTracker(
            os.path.join(self.test_folder, "tests.logs")
        )

        # ---- Yield access to test function ----
        yield self.test_folder
        # ---- Yield access to test function ----

        # ---- Process work dir ----
        rep_call = getattr(request.node, "rep_call", None)
        keep_dir = request.config.getoption("--keep-test-dir")

        if rep_call is not None and rep_call.failed:
            os.rename(
                self.test_folder,
                os.path.join(test_abs_parent_folder, test_dir_name_failed),
            )
        elif keep_dir:
            os.rename(
                self.test_folder,
                os.path.join(test_abs_parent_folder, test_dir_name_succeed),
            )
        else:
            shutil.rmtree(self.test_folder, ignore_errors=True)
        # ---- Process work dir ----

        return self.test_folder

    # ---- ---- Screening ---- ----
    def screen_var(self, name: str, obj: typing.Any) -> None:
        """LogFile.screen wrapper"""
        self.tracker.screen(name, obj)

    def re_screen_var(self, name: str, obj=None) -> None:
        """LogFile.re_screen wrapper"""
        self.tracker.re_screen(name, obj)

    def re_screen_all(self) -> None:
        """LogFile.re_screen_all wrapper"""
        self.tracker.re_screen_all()

    # ---- ---- Screening ---- ----

    # ---- ---- Logging ---- ----
    def log(self, *msg: str, end: str = "\n", tab: str = "") -> None:
        """write a message inside the log file. Each line will be
        separated by <end> + <tab> and <end> will be added at the end of
        the message."""
        self.tracker.write(f"{end}{tab}".join(msg), end=end)

    # ---- ---- Logging ---- ----

    # ---- ---- os wrapper ---- ----
    @staticmethod
    def file_exist(path: str) -> bool:
        """os.path.isfile wrapper"""
        return os.path.isfile(path)

    @staticmethod
    def folder_exist(path: str) -> bool:
        """os.path.isdir wrapper"""
        return os.path.isdir(path)

    @staticmethod
    def path_exist(path: str) -> bool:
        """os.path.exists wrapper"""
        return os.path.exists(path)

    # ---- ---- os wrapper ---- ----
    @staticmethod
    def contains_pattern(pattern: str, string: str):
        """
        :return:  Does this string contain a patter
        :param str pattern: A regex
        :param str string: A string
        """
        return re.search(pattern, string) is not None

    @staticmethod
    def get_fresh_class(class_):
        """Returns an independent class that copy <class_>."""
        return types.new_class(class_.__name__ + "ForTest", (class_,))
