import datetime
import difflib
import os
import pprint
import re
import shutil
import types
import typing
from inspect import getfile

import pytest


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
    In this folder a tests.logs file is generated through a LogFile. This LogFile allows
    var screening.

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
        self.logs = LogFile(os.path.join(self.test_folder, "tests.logs"))

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
        self.logs.screen(name, obj)

    def re_screen_var(self, name: str, obj=None) -> None:
        """LogFile.re_screen wrapper"""
        self.logs.re_screen(name, obj)

    def re_screen_all(self) -> None:
        """LogFile.re_screen_all wrapper"""
        self.logs.re_screen_all()

    # ---- ---- Screening ---- ----

    # ---- ---- Logging ---- ----
    def log(self, *msg: str, end: str = "\n", tab: str = "") -> None:
        """write a message inside the log file. Each line will be
        separated by <end> + <tab> and <end> will be added at the end of
        the message."""
        self.logs.write(f"{end}{tab}".join(msg), end=end)

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


class LogFile:
    """
    A small class that represent a file that contains logs.
    Using this class, you can watch the evolution of a variable
    by screening it with <screen> and <re_screen>.
    """

    class ScreenVar:
        """
        A class that contains an object and that extract debug information from it.
        """

        def __init__(self, opened_file, name, obj, screen_now: bool=True):
            self.name = name
            self.obj = obj
            self.opened_file = opened_file
            self._old_screen = None
            self.content = None
            self.size = None
            self.type = None

            if screen_now:
                self.screen()

        @staticmethod
        def _diff(s1: str, s2: str) -> str:
            lines1 = s1.splitlines()
            lines2 = s2.splitlines()

            return "\n".join(difflib.ndiff(lines1, lines2))

        def screen(self):
            """Screen the contained object"""
            self._screen()
            self.export()

        def re_screen(self, obj: typing.Any = None):
            """Screen again the contained object.
            Ypu can modify this object with <obj>"""
            if obj:
                self.obj = obj
            self.screen()

        def export(self):
            """
            Export debug intel from self.obj to the log file.
            """

            new_screen = pprint.pformat(self.content)
            self.opened_file.write(f"\n[Start {self.name}]\n")

            if self._old_screen:
                self.opened_file.write(self._diff(self._old_screen, new_screen))
            else:
                self.opened_file.write(new_screen)

            self.opened_file.write(f"\n[End {self.name}]\n")
            self._old_screen = new_screen

        def _screen(self):
            """Update intel related to self.obj"""
            self.type = type(self.obj).__name__
            obj_attr = dir(self.obj)
            try:
                self.size = self.obj.__sizeof__()
            except TypeError:
                self.size = None

            if isinstance(self.obj, (str, list, dict, set, tuple)):
                self.content = self.obj
            else:
                self.content = (
                    self.obj.__dict__
                    if "__dict__" in obj_attr
                    else self.obj.__repr__
                )

    def __init__(self, file_path: str):
        """
        :param str file_path: Where logs should be written (no file allowed)
        """
        self.path = os.path.abspath(file_path)
        self.screen_vars: dict[str, LogFile.ScreenVar] = {}

        if os.path.exists(file_path):
            raise FileExistsError(
                f"Can not write log in '{file_path}' (file exist)"
            )
        if not os.path.isdir(os.path.dirname(file_path)):
            raise FileExistsError(
                f"Can not write log in '{file_path}' (unknown folder)"
            )

        # pylint: disable=R1732
        # flux should stay opened while this pbject exist
        self.flux = open(self.path, "a", encoding="utf-8")

    def write(self, text: str, end: str = "\n") -> None:
        """
        Write text inside the log file. use <end> to add a char at the end of your text (usually \n)
        """
        self.flux.write(text)
        self.flux.write(end)

    def screen(self, name: str, obj: typing.Any) -> ScreenVar:
        """
        Screen a variable.
        :param str name: name of the variable in log file
        :param obj: any object / var to screen
        """
        sv = self.ScreenVar(self.flux, name, obj)
        self.screen_vars[name] = sv
        return sv

    def re_screen(self, sv_or_name: str | ScreenVar, obj=None) -> None:
        """
        Screen a variable again.
        :param sv_or_name: ScreenVar or var name.
        :param obj: Use it if the object needs to be changed.
        """
        if not isinstance(sv_or_name, self.ScreenVar):
            sv_or_name = self.screen_vars[sv_or_name]
        sv_or_name.re_screen(obj)

    def re_screen_all(self) -> None:
        """Re screen all screened variables."""
        for _, sv in self.screen_vars.items():
            self.re_screen(sv)
