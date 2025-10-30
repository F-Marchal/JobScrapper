from sql.filters.filter_part import FilterPart, STRING_TO_COMPARISON_WRAPPERS, STRING_TO_LOGICAL_WRAPPERS
from sql.tables.jobs import Jobs
from sql.tables.places.distances import Distances
from tests.conftest import BaseTest
import pytest
from typing import Any
from sqlalchemy.sql import operators as ope
from sqlalchemy import case, func

@pytest.mark.sql_filters
class TestFilterPart(BaseTest):
    """Test FilterPart generation"""
    #####################################
    #           Initialisation          #
    #####################################
    def test_minimal_initialisation(self):
        """Test initialisation using only url"""
        kwargs = self.common_kwargs()

        fp = FilterPart("Url", **kwargs)
        self.screen_var("fp", fp)
        assert fp
        assert fp.str_column == "url"
        assert fp.column == kwargs["string_to_columns"]["url"]
        assert fp.comp_operator is None
        assert fp.start_parenthesis is False
        assert fp.close_parenthesis is False
        


    @pytest.mark.parametrize(
        "raw_string, column_name, comp_op, comp_value",
        [
            ("url::>=::5", "url", ">=", 5),
            ("Url::<=::5.65", "url", "<=", 5.65),
            ("Url::==::Alpha", "url", "==", "Alpha"),
            ("Url::!=::5", "url", "!=", 5),
        ],
    )
    def test_comp_initialisation(
            self,
            raw_string: str,
            column_name: str,
            comp_op: str,
            comp_value: Any
    ):
        """Test initialisation using url::comparator:value"""
        kwargs = self.common_kwargs()

        fp = FilterPart(raw_string, **kwargs)
        self.screen_var("fp", fp)
        assert fp
        assert fp.str_column == column_name
        assert fp.column == kwargs["string_to_columns"][column_name]
        assert fp.comp_operator is not None
        assert fp.comp_operator == STRING_TO_COMPARISON_WRAPPERS[comp_op]
        assert fp.comp_value == comp_value
        assert fp.start_parenthesis is False
        assert fp.close_parenthesis is False

    @pytest.mark.parametrize(
        "raw_string, column_name, comp_op, comp_value, logic_op",
        [
            ("&::Url::<=::5.65", "url", "<=", 5.65, "&"),
            ("|::Url::==::Alpha", "url", "==", "Alpha", "|"),
            ("^::Url::!=::5", "url", "!=", 5, "^"),
        ],
    )
    def test_logic_initialisation(
            self,
            raw_string: str,
            column_name: str,
            comp_op: str,
            comp_value: Any,
            logic_op: str,
    ):
        """Test initialisation using operator::url::comparator:value"""
        kwargs = self.common_kwargs()
        fp = FilterPart(raw_string, **kwargs)
        self.screen_var("fp", fp)
        assert fp
        assert fp.str_column == column_name
        assert fp.column == kwargs["string_to_columns"][column_name]
        assert fp.comp_operator is not None
        assert fp.comp_operator == STRING_TO_COMPARISON_WRAPPERS[comp_op]
        assert fp.comp_value == comp_value
        assert fp.logic_operator == STRING_TO_LOGICAL_WRAPPERS[logic_op]
        assert fp.start_parenthesis is False
        assert fp.close_parenthesis is False

    @pytest.mark.parametrize(
        "raw_string, column_name, comp_op, comp_value, logic_op, open_, close",
        [
            (")::&::Url::<=::5.65", "url", "<=", 5.65, "&", False, True),
            (")(::|::Url::==::Alpha", "url", "==", "Alpha", "|", True, True),
            ("(::^::Url::!=::5", "url", "!=", 5, "^", True, False),
        ],
    )
    def test_par_initialisation(
            self,
            raw_string: str,
            column_name: str,
            comp_op: str,
            comp_value: Any,
            logic_op: str,
            open_: bool,
            close: bool,
    ):
        """Test initialisation using parenthesis::operator::url::comparator:value"""
        kwargs = self.common_kwargs()
        fp = FilterPart(raw_string, **kwargs)
        self.screen_var("fp", fp)
        assert fp
        assert fp.str_column == column_name
        assert fp.column == kwargs["string_to_columns"][column_name]
        assert fp.comp_operator is not None
        assert fp.comp_operator == STRING_TO_COMPARISON_WRAPPERS[comp_op]
        assert fp.comp_value == comp_value
        assert fp.logic_operator == STRING_TO_LOGICAL_WRAPPERS[logic_op]
        assert fp.start_parenthesis is open_
        assert fp.close_parenthesis is close

    def test_failed_initialisation__unknown_column(self):
        """Test initialisation using a column that does not exist"""
        kwargs = self.common_kwargs()
        fp = FilterPart("Foo54", **kwargs)
        self.screen_var("fp", fp)
        assert not fp
        assert fp.str_column == ""
        assert fp.column is None
        assert fp.comp_operator is None
        assert fp.start_parenthesis is False
        assert fp.close_parenthesis is False

    def test_failed_initialisation__one_column_sep(self):
        """Test initialisation using a format that does not exist"""
        kwargs = self.common_kwargs()
        fp = FilterPart("url::<=", **kwargs)
        self.screen_var("fp", fp)
        assert fp
        assert fp.str_column == "url"
        assert fp.column is kwargs["string_to_columns"]["url"]
        assert fp.comp_operator is None
        assert fp.start_parenthesis is False
        assert fp.close_parenthesis is False

    def test_generate_new_column(self):
        """Ensure that generate_column_using works as intended :
        - Update string_to_columns
        - does fp works with 'unknown' column.
        """

        gcu = lambda col_name: func.max(
            case(
                (
                    ope.eq(
                        Distances.reference_localisation,
                        col_name.lower()
                    ),
                    Distances.distance
                ),
                else_=None
            )
        ).label(col_name + "_test")
        kwargs = self.common_kwargs()
        assert "alpha" not in kwargs["string_to_columns"]
        fp = FilterPart("alpha::<=::50", **kwargs, generate_column_using=gcu)
        assert fp
        assert fp.str_column == "alpha"
        assert fp.column is not None
        assert "alpha" in fp.string_to_columns
        assert "alpha" in kwargs["string_to_columns"]
    
    #####################################
    #                UTILS              #
    #####################################
    @staticmethod
    def common_kwargs():
        """Returns kwargs used by (almost) all FilterPart during tests."""
        return {
            "string_to_columns": Jobs.get_columns_using_sql_name(),
            "string_formater": lambda s: s.lower()
        }