import pytest
from sqlalchemy import Column, Integer, String

from sql.tables.base_table import BaseTable
from sql.tables.helpers.sql_request_wrapper import SQLRequestWrapper
from tests.conftest import BaseTest
from tools.logger_core import CoreLogger


@pytest.mark.sqlalchemy_wrappers
class TestSqlRequestWrapper(BaseTest):
    """Test SqlRequestWrapper functionalities"""

    def test_suffixes(self):
        """Test Suffix related methods"""

        srw1 = SQLRequestWrapper()
        srw2 = SQLRequestWrapper(
            suffixes={"Alpha": "A", "Number": "#"},
            column_name_normaliser=lambda string: string.lower(),
        )

        assert not srw1.suffixes
        assert not srw1.get_suffix("Alpha") == "A"
        assert not srw1.get_suffix("Number") == "#"

        assert srw2.suffixes
        assert srw2.suffixes["Alpha"] == "A"
        assert srw2.suffixes["Number"] == "#"

        srw1.set_suffixes(alpha="b")
        assert srw1.get_suffix("Alpha") == ""
        assert srw1.get_suffix("alpha") == "b"
        assert srw1.get_suffix("Number") == ""

    def test_basic_request(self):
        """Test to request a small database with not filters"""
        db = f"{self.test_folder}/database.db"
        self.make_small_db(db)
        sql_rw = SQLRequestWrapper(
            column_name_normaliser=lambda string: string.title(),
            column_label_value_normaliser=lambda string: string.lower(),
            logger=CoreLogger.logger,
        )
        sql_rw.set_suffixes(
            default=" #",
        )
        self.screen_var("sql_rw", sql_rw)

        filter_generator = sql_rw.quick_filter_generator(
            table=self.TestLookupTable,
            columns=["Alpha", "beta", "Gamma"],
            column_creator=sql_rw.quick_column_creator(
                label_col=self.TestLookupTable.label,
                value_col=self.TestLookupTable.value,
                else_value=-1,
                suffix_name="default",
            ),
        )
        self.screen_var("filter_", filter_generator)

        # Does all 3 columns has been generated
        assert len(filter_generator.columns) == 3

        # Does column_name_normaliser was applied ? (.title)
        # Does prefix was applied ? (' #')
        for cols in filter_generator.columns:
            assert cols.name in ("Alpha #", "Beta #", "Gamma #")

        with self.TestLookupTable.get_session(db) as session:
            query = (
                session.query(
                    self.TestLookupTable.fk, *filter_generator.columns
                )
                .group_by(self.TestLookupTable.fk)
                .order_by(
                    self.TestLookupTable.fk,
                )
            )
            result = sql_rw.execute_request(session, query)

        assert set(result.keys()) == {"fk", "Alpha #", "Beta #", "Gamma #"}

        for i, vals in enumerate(result.all()):
            assert len(vals) == 4
            fk, alpha, beta, gamma = vals

            # Ensure that order by works
            assert i + 1 == fk

            if fk == 1:
                assert (alpha, beta, gamma) == (4, 5, -1)
            elif fk == 2:
                assert (alpha, beta, gamma) == (-1, 15, 1)
            elif fk == 3:
                assert (alpha, beta, gamma) == (42, -1, -1)

    def test_filtered_request(self):
        """Test to request a small database using filters"""
        db = f"{self.test_folder}/database.db"
        self.make_small_db(db)
        sql_rw = SQLRequestWrapper(
            column_name_normaliser=lambda string: string.title(),
            column_label_value_normaliser=lambda string: string.lower(),
            logger=CoreLogger.logger,
        )
        sql_rw.set_suffixes(
            default=" #",
        )
        self.screen_var("sql_rw", sql_rw)

        filter_generator = sql_rw.quick_filter_generator(
            table=self.TestLookupTable,
            columns=["Alpha::>=::5", "beta", "Gamma"],
            column_creator=sql_rw.quick_column_creator(
                label_col=self.TestLookupTable.label,
                value_col=self.TestLookupTable.value,
                else_value=-1,
                suffix_name="default",
            ),
        )
        self.screen_var("filter_", filter_generator)

        # Does all 3 columns has been generated
        assert len(filter_generator.columns) == 3

        # Does column_name_normaliser was applied ? (.title)
        # Does prefix was applied ? (' #')
        for cols in filter_generator.columns:
            assert cols.name in ("Alpha #", "Beta #", "Gamma #")

        with self.TestLookupTable.get_session(db) as session:
            query = (
                session.query(
                    self.TestLookupTable.fk, *filter_generator.columns
                )
                .group_by(self.TestLookupTable.fk)
                .having(filter_generator.filters)
                .order_by(
                    self.TestLookupTable.fk,
                )
            )
            result = sql_rw.execute_request(session, query)

        assert set(result.keys()) == {"fk", "Alpha #", "Beta #", "Gamma #"}
        all_ = result.all()
        assert len(all_) == 1
        assert all_[0] == (3, 42, -1, -1)

    #############################
    #           Utils           #
    #############################
    class TestLookupTable(BaseTable):
        """Small lookup table for test purposes"""

        __abstract__ = False
        __tablename__ = "TestLookupTable"
        fk = Column(Integer, primary_key=True, nullable=False)
        label = Column(String, primary_key=True, nullable=False)
        value = Column(Integer, primary_key=False, nullable=True)

    def make_small_db(self, path: str):
        """Generate a small database of lookup table"""
        entries = [
            self.TestLookupTable(fk=1, label="alpha", value=4),
            self.TestLookupTable(fk=1, label="beta", value=5),
            self.TestLookupTable(fk=2, label="gamma", value=1),
            self.TestLookupTable(fk=2, label="beta", value=15),
            self.TestLookupTable(fk=3, label="alpha", value=42),
        ]

        self.screen_multiple_vars("TLT", *entries)
        with self.TestLookupTable.get_session(path) as s:
            s.add_all(entries)
