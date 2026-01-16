import typing

import pytest

from tests.conftest import BaseTest


@pytest.mark.testModules
class TestVariableTracker(BaseTest):
    """Test VariableTracker using the BaseTest.tracker's VariableTracker. (As the uniq purpose
    of VariableTracker is to be used through)"""

    @pytest.mark.parametrize("value", ["Hello", 42, 19.76514, False, None])
    def test_screen_basic_type(self, value: str | int | float | bool | None):
        """Test <self.tracker.screen> of a dictionary"""
        name = f"Test {type(value).__name__}"
        self.tracker.screen(name, value)

        name_pattern = f"'name': '{name}'"
        content_pattern = f"'content': '{value}'"
        type_pattern = f"'type': '{ type(value).__name__}'"
        content = "".join(self.tracker.get_content())

        assert self.contains_pattern(name_pattern, content)
        assert self.contains_pattern(content_pattern, content)
        assert self.contains_pattern(type_pattern, content)

    @pytest.mark.parametrize(
        "value",
        [
            ["A", None, 34, True],
            {"A", None, 34, True},
            ("A", None, 34, True),
        ],
    )
    def test_screen_sequence_type(self, value: typing.Sequence):
        """Test <self.tracker.screen> of a list / set / tuple"""
        name = f"Test-{type(value)}"
        self.tracker.screen(name, value)
        content = "\n".join(self.tracker.get_content())

        name_pattern = rf"'name'.*:.*{name}"
        content_pattern = rf"'content'.*:.*{'.*'.join([str(v) for v in value])}"
        type_pattern = rf"'type'.*:.*{ type(value).__name__}"
        self.tracker.write("[Patterns]")

        assert self.contains_pattern(name_pattern, content)
        assert self.contains_pattern(content_pattern, content)
        assert self.contains_pattern(type_pattern, content)

    def test_screen_dict_and_rescreen(self):
        """Test <self.tracker.screen> of a dictionary"""
        dict_ = {"a": 2, None: True, 45.0: "string"}
        name = f"Test-{type(dict_)}"
        self.tracker.screen(name, dict_)

        del dict_["a"]
        del dict_[None]
        del dict_[45.0]
        dict_[4] = 55
        dict_["44"] = 11
        self.tracker.re_screen_all()

        content = "".join(self.tracker.get_content())

        assert self.contains_pattern(
            r"{'content': {None: True, 45.0: 'string', 'a': 2},", content
        )
        assert self.contains_pattern(
            r"- {'content': {None: True, 45.0: 'string', 'a': 2},", content
        )
        assert self.contains_pattern(
            r"\+ {'content': {4: 55, '44': 11},", content
        )

    def test_screen_custom_class(self):
        """Test <self.tracker.screen> of a CustomClass (Object + class)"""

        class CustomClass:
            """Test class"""

            cls_arg = 775

            def __init__(self):
                self.s_arg = 44

        self.tracker.screen("CustomClass", CustomClass)
        self.tracker.screen("CustomObject", CustomClass())

        content = "".join(self.tracker.get_content())
        class_pattern = "'cls_arg': 775"
        object_pattern = "'content': {'s_arg': 44}"

        assert self.contains_pattern(class_pattern, content)
        assert self.contains_pattern(object_pattern, content)
