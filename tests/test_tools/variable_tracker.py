import difflib
import os
import pprint
import typing


class VariableTracker:
    """
    A small class that represent a file that intel related to a tracked variable.
    Using this class, you can watch the evolution of a variable
    by screening it with <screen> and <re_screen>.
    """

    class ScreenVar:
        """
        A class that contains an object and that extract debug information from it.
        """

        def __init__(self, tracker, name, obj, screen_now: bool = True):
            self.name = name
            self.obj = obj
            self.tracker = tracker
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

        @property
        def content_dict(self) -> dict:
            return {
                "name": self.name,
                "type": self.type,
                "size": self.size,
                "content": self.content,
            }

        def export(self):
            """
            Export debug intel from self.obj to the log file.
            """

            new_screen = pprint.pformat(
                self.content_dict
            )

            self.tracker.write(f"[Start {self.name}]")

            if self._old_screen:
                self.tracker.write(self._diff(self._old_screen, new_screen))
            else:
                self.tracker.write(new_screen)

            self.tracker.write(f"[End {self.name}]")

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
                    else self.obj.__repr__()
                )

    def __init__(self, file_path: str):
        """
        :param str file_path: Where logs should be written (no file allowed)
        """
        self.path = os.path.abspath(file_path)
        self.screen_vars: dict[str, VariableTracker.ScreenVar] = {}

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
        self.flux = open(self.path, "a+", encoding="utf-8")

    def write(self, text: str, end: str = "\n") -> None:
        """
        Write text inside the log file. use <end> to add a char at the end of your text (usually \n)
        """
        self.flux.write(text)
        self.flux.write(end)

    def get_content(self):
        """Return log content."""
        self.flux.seek(0)
        return self.flux.readlines()

    def screen(self, name: str, obj: typing.Any) -> ScreenVar:
        """
        Screen a variable.
        :param str name: name of the variable in log file
        :param obj: any object / var to screen
        """
        sv = self.ScreenVar(self, name, obj)
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
