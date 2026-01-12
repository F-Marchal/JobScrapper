import os.path
from datetime import datetime

import pytest
from sqlalchemy import Column, DateTime, Float, Integer, String

from job_scrapper.sql import BaseTable
from tests.conftest import BaseTest
from job_scrapper.tools.logger_core import CoreLogger

NOW = datetime.now()

# pylint: disable=R0904
# We use many public method to do many tests
@pytest.mark.js_tables
class TestBaseTable(BaseTest):
    """Test BaseTable's methods"""

    # ===================================== #
    #             js_tables_pyt             #
    # ===================================== #
    @pytest.mark.js_tables_pyt
    def test_get_column_using_sql_name(self):
        """Ensure that get_columns_using_sql_name returns the correct content."""
        cusn = self.TestBaseTable.get_columns_using_sql_name()
        self.screen_var("cusn", cusn)
        assert cusn["strid"] == self.TestBaseTable.string_id
        assert cusn["intid"] == self.TestBaseTable.integer_id
        assert cusn["value"] == self.TestBaseTable.value
        assert cusn["time_stamp"] == self.TestBaseTable.time_stamp

    @pytest.mark.js_tables_pyt
    def test_get_columns_using_attr_name(self):
        """Ensure that get_columns_using_attr_name returns the correct content."""
        cuan = self.TestBaseTable.get_columns_using_attr_name()
        self.screen_var("cuan", cuan)

        assert cuan["string_id"] == self.TestBaseTable.string_id
        assert cuan["integer_id"] == self.TestBaseTable.integer_id
        assert cuan["value"] == self.TestBaseTable.value
        assert cuan["time_stamp"] == self.TestBaseTable.time_stamp

    # --- get columns ---
    @pytest.mark.js_tables_pyt
    def test_get_pk_attr_name(self):
        """Ensure that get_pk_col_attr_name returns the correct content."""
        assert BaseTable.get_pk_col_attr_name() == {}

        pk_cols = self.TestBaseTable.get_pk_col_attr_name()
        assert "string_id" in pk_cols
        assert "integer_id" in pk_cols
        assert "value" not in pk_cols
        assert "time_stamp" not in pk_cols

    @pytest.mark.js_tables_pyt
    def test_get_non_pk_attr_name(self):
        """Ensure that get_non_pk_col_attr_name returns the correct content."""
        assert BaseTable.get_non_pk_col_attr_name() == {}

        pk_cols = self.TestBaseTable.get_non_pk_col_attr_name()
        assert "string_id" not in pk_cols
        assert "integer_id" not in pk_cols
        assert "value" in pk_cols
        assert "time_stamp" in pk_cols

    # --- to_dicts ---
    @pytest.mark.js_tables_pyt
    def test_to_dict(self):
        """Ensure that to_dict returns the correct content with correct types."""
        obj = self.make_one_entry()
        to_dict = obj.to_dict()
        self.screen_var("to_dict", to_dict)

        assert "string_id" in to_dict
        assert "integer_id" in to_dict
        assert "value" in to_dict
        assert "time_stamp" in to_dict

        assert to_dict["string_id"] == "AnId"
        assert to_dict["integer_id"] == 42
        assert to_dict["value"] == 63.45
        assert to_dict["time_stamp"] == NOW

    @pytest.mark.js_tables_pyt
    def test_to_pk_dict(self):
        """Ensure that to_pk_dict returns the correct content with correct types."""
        obj = self.make_one_entry()
        to_dict = obj.to_pk_dict()
        self.screen_var("to_pk_dict", to_dict)

        assert "string_id" in to_dict
        assert "integer_id" in to_dict
        assert "value" not in to_dict
        assert "time_stamp" not in to_dict

        assert to_dict["string_id"] == "AnId"
        assert to_dict["integer_id"] == 42
        # assert to_dict["value"] == 63.45
        # assert to_dict["time_stamp"] == NOW

    @pytest.mark.js_tables_pyt
    def test_to_non_pk_dict(self):
        """Ensure that to_non_pk_dict returns the correct content with correct types."""
        obj = self.make_one_entry()
        to_dict = obj.to_non_pk_dict()
        self.screen_var("to_non_pk_dict", to_dict)

        assert "string_id" not in to_dict
        assert "integer_id" not in to_dict
        assert "value" in to_dict
        assert "time_stamp" in to_dict

        # assert to_dict["string_id"] == "AnId"
        # assert to_dict["integer_id"] == 42
        assert to_dict["value"] == 63.45
        assert to_dict["time_stamp"] == NOW

    # --- flat ---
    @pytest.mark.js_tables_pyt
    def test_flat(self):
        """Ensure that test_flat returns a string correctly formated.
        Those strings should be equals for each entry with the same cols and col's value
        """
        obj1, obj2 = self.make_two_identical_entries()

        assert obj1.to_dict() == obj1.to_dict()
        assert obj2.flat() == obj1.flat()

    @pytest.mark.js_tables_pyt
    def test_flat_pk(self):
        """Ensure that test_flat returns a string correctly formated.
        Those strings should be equals for each entry with the same cols and col's value
        """
        obj1, obj2 = self.make_two_equ_entries()

        assert obj1.to_pk_dict() == obj1.to_pk_dict()
        assert obj2.flat_pk() == obj1.flat_pk()

    @pytest.mark.js_tables_pyt
    def test_flat_non_pk(self):
        """Ensure that test_flat returns a string correctly formated.
        Those strings should be equals for each entry with the same cols and col's value
        """
        obj1, obj2 = self.make_two_identical_entries()

        assert obj1.to_dict() == obj1.to_dict()
        assert obj2.to_non_pk_dict() == obj1.to_non_pk_dict()
        assert obj2.flat_non_pk() == obj1.flat_non_pk()

    # --- Get existing ---
    @pytest.mark.js_tables_pyt
    def test__eq__(self):
        """Ensure that BaseTableForJobScrapper comparisons are correctly done"""
        e1, e2 = self.make_two_equ_entries()
        e3, e4 = self.make_two_identical_entries()
        assert e1 != e2
        assert e3 == e4

    def test_are_equivalent(self):
        """Ensure that BaseTableForJobScrapper comparisons are correctly done"""
        e1, e2 = self.make_two_identical_entries()
        assert BaseTable.are_equivalent(e1, e2, strict=False)
        assert BaseTable.are_equivalent(e1, e2, strict=True)

        # e1 and e2 are equivalents but not equals
        e1.value += 45
        assert BaseTable.are_equivalent(e1, e2, strict=False)
        assert not BaseTable.are_equivalent(e1, e2, strict=True)

        # e1 and e2 are not equivalents anymore
        e1.integer_id += 45
        assert not BaseTable.are_equivalent(e1, e2, strict=False)
        assert not BaseTable.are_equivalent(e1, e2, strict=True)

    @pytest.mark.js_tables_pyt
    def test_equivalent_to(self):
        """Ensure that BaseTableForJobScrapper comparisons are correctly done"""
        e1, e2 = self.make_two_identical_entries()

        # e1 and e2 are fully equals
        assert e1.is_equivalent_to(e1, strict=True)
        assert e1.is_equivalent_to(e2, strict=True)
        assert e2.is_equivalent_to(e1, strict=True)
        assert e2.is_equivalent_to(e2, strict=True)

        assert e1.is_equivalent_to(e1, strict=True)
        assert e1.is_equivalent_to(e2, strict=True)
        assert e2.is_equivalent_to(e1, strict=True)
        assert e2.is_equivalent_to(e2, strict=True)

        # e1 and e2 are equivalents but not equals
        e1.value += 45

        assert e1.is_equivalent_to(e2, strict=False)
        assert not e1.is_equivalent_to(e2, strict=True)
        assert e2.is_equivalent_to(e1, strict=False)
        assert not e2.is_equivalent_to(e1, strict=True)

        # e1 and e2 are not equivalents anymore
        e1.integer_id += 45
        assert not e1.is_equivalent_to(e2, strict=False)
        assert not e1.is_equivalent_to(e2, strict=True)
        assert not e2.is_equivalent_to(e1, strict=False)
        assert not e2.is_equivalent_to(e1, strict=True)

    @pytest.mark.js_tables_pyt
    def test___copy__(self):
        """Ensure that __copy__ and copy works as intended"""
        e1 = self.make_one_entry()
        e2 = e1.copy()
        self.screen_var("copy", e2)

        assert e1.to_dict() == e2.to_dict()

    # ===================================== #
    #     js_tables_sql / js_tables_pyt     #
    # ===================================== #
    @pytest.mark.js_tables_pyt
    @pytest.mark.js_tables_sql
    def test_get_existing_self(self):
        """Ensure that get_existing_self returns the correct instances in the correct situation"""
        # pylint: disable=R0915:
        # We are at 51/50, I do not have time to breack this function appart

        e1, e2 = self.make_two_identical_entries()
        # e3 and e4 might have different datetime.
        e3, e4 = self.make_two_identical_entries()
        e3.integer_id += 1
        e4.value += 1
        db1 = f"{self.test_folder}/database1.db"

        # Exist only inside the session :
        with BaseTable.get_session(db1) as session:
            assert (
                e2.get_existing_self(
                    session, include_session=False, include_database=False
                )
                is None
            )
            session.add(e1)
            assert (
                e2.get_existing_self(
                    session, include_session=False, include_database=False
                )
                is None
            )

            assert e1.get_existing_self(session) is None
            assert e2.get_existing_self(session) is None

            # When it should work
            existing1 = e1.get_existing_self(
                session, strict=True, include_session=True
            )
            existing2 = e2.get_existing_self(
                session, strict=True, include_session=True
            )
            existing4 = e4.get_existing_self(
                session, strict=False, include_session=True
            )

            assert existing1 is not None
            assert existing2 is not None
            assert existing4 is not None

            assert existing1 == existing2
            assert existing4 == existing2

            # When it should not work
            assert (
                e4.get_existing_self(session, strict=True, include_session=True)
                is None
            )
            assert (
                e3.get_existing_self(
                    session, strict=False, include_session=True
                )
                is None
            )

        # Exist only inside the database :
        with BaseTable.get_session(db1) as session:
            assert (
                e2.get_existing_self(
                    session, include_session=False, include_database=False
                )
                is None
            )

            # When it should work
            existing2 = e2.get_existing_self(session, strict=True)
            existing4 = e4.get_existing_self(session, strict=False)

            assert existing2 is not None
            assert existing4 is not None
            assert existing4 == existing2

            # When it should not work
            assert e4.get_existing_self(session, strict=True) is None
            assert e3.get_existing_self(session, strict=False) is None

            # test include_database = False
            assert (
                e2.get_existing_self(
                    session, strict=True, include_database=False
                )
                is None
            )
            assert (
                e4.get_existing_self(
                    session, strict=True, include_database=False
                )
                is None
            )

        # Exist both inside the database and the session:
        with BaseTable.get_session(db1) as session:
            session.add(e4)

            # Expect e4 format (e1 is in the session)
            existing4_s = e4.get_existing_self(
                session, include_database=False, include_session=True
            )
            assert BaseTable.are_equivalent(e4, existing4_s, strict=True)
            assert BaseTable.are_equivalent(e4, existing4_s, strict=False)
            assert not BaseTable.are_equivalent(e2, existing4_s, strict=True)

            # Expect e1 / e2 format (e1 has been exported inside the database)
            existing4_d = e4.get_existing_self(
                session, include_database=True, include_session=False
            )
            assert not BaseTable.are_equivalent(e4, existing4_d, strict=True)
            assert BaseTable.are_equivalent(e4, existing4_d, strict=False)
            assert BaseTable.are_equivalent(e2, existing4_d, strict=True)

            # Expect same result as first experiment. session has a bigger priority.
            existing4_b = e4.get_existing_self(
                session, include_database=True, include_session=True
            )
            assert BaseTable.are_equivalent(e4, existing4_b, strict=True)
            assert BaseTable.are_equivalent(e4, existing4_b, strict=False)
            assert not BaseTable.are_equivalent(e2, existing4_b, strict=True)

            # Test with e2. Instance returned should be like e4 (e4 in session.new)
            existing2_b = e2.get_existing_self(
                session, include_database=True, include_session=True
            )
            assert not BaseTable.are_equivalent(e2, existing2_b, strict=True)
            assert BaseTable.are_equivalent(e2, existing4_b, strict=False)
            assert BaseTable.are_equivalent(e4, existing2_b, strict=True)

    @pytest.mark.js_tables_pyt
    @pytest.mark.js_tables_sql
    def test_exists(self):
        """.exist is mostly based on <test_get_existing_self>. I assume that if test_get_existing_self pass,
        we do not need extensive test here."""
        e1, e2 = self.make_two_identical_entries()
        e3, e4 = self.make_two_identical_entries()
        e3.integer_id += 1
        e4.value += 1

        db1 = f"{self.test_folder}/database1.db"
        # In session.new
        with BaseTable.get_session(db1) as session:
            session.add(e1)
            assert not e1.exists(
                session, include_session=False, include_database=True
            )
            assert not e1.exists(
                session, include_session=False, include_database=False
            )
            assert e1.exists(
                session, include_session=True, include_database=False
            )

            assert not e2.exists(
                session,
                include_session=False,
                include_database=True,
                strict=True,
            )
            assert not e2.exists(
                session,
                include_session=False,
                include_database=False,
                strict=True,
            )
            assert e2.exists(
                session,
                include_session=True,
                include_database=False,
                strict=True,
            )

            assert not e4.exists(
                session,
                include_session=False,
                include_database=True,
                strict=True,
            )
            assert not e4.exists(
                session,
                include_session=False,
                include_database=False,
                strict=True,
            )
            assert not e4.exists(
                session,
                include_session=True,
                include_database=False,
                strict=True,
            )

            assert not e4.exists(
                session, include_session=False, include_database=True
            )
            assert not e4.exists(
                session, include_session=False, include_database=False
            )
            assert e4.exists(
                session, include_session=True, include_database=False
            )

        # In database
        with BaseTable.get_session(db1) as session:
            assert e2.exists(
                session,
                include_session=False,
                include_database=True,
                strict=True,
            )
            assert not e2.exists(
                session,
                include_session=False,
                include_database=False,
                strict=True,
            )
            assert not e2.exists(
                session,
                include_session=True,
                include_database=False,
                strict=True,
            )

            assert not e4.exists(
                session,
                include_session=False,
                include_database=True,
                strict=True,
            )
            assert not e4.exists(
                session,
                include_session=False,
                include_database=False,
                strict=True,
            )
            assert not e4.exists(
                session,
                include_session=True,
                include_database=False,
                strict=True,
            )

            assert e4.exists(
                session, include_session=False, include_database=True
            )
            assert not e4.exists(
                session, include_session=False, include_database=False
            )
            assert not e4.exists(
                session, include_session=True, include_database=False
            )

        # In session.dirty
        with BaseTable.get_session(db1) as session:
            e2_from_database = e2.get_existing_self(
                session, include_database=True, include_session=False
            )
            e2_from_database.integer_id = e3.integer_id

            assert len(session.new) == 0
            assert len(session.dirty) == 1
            assert not e3.exists(
                session, include_session=False, include_database=True
            )
            assert not e3.exists(
                session, include_session=False, include_database=False
            )
            assert e3.exists(
                session, include_session=True, include_database=False
            )

    # ===================================== #
    #             js_tables_sql             #
    # ===================================== #
    @pytest.mark.js_tables_sql
    def test_get_session(self):
        """
        Test the get_session command (and all sub commands)
        - get_kNOWn_databases
        - _get_engine
        - get_session
        - _sanitise_and_commit (empty content)
        - create_all
        -
        """
        # Database creation :
        db1 = f"{self.test_folder}/database1.db"
        db2 = f"{self.test_folder}/database2.db"
        assert not os.path.exists(db1)
        assert not os.path.exists(db2)

        with BaseTable.get_session(db1):
            pass

        with BaseTable.get_session(db2):
            pass

        assert os.path.exists(db1)
        assert os.path.exists(db2)

        assert db1 in BaseTable.get_known_databases()
        assert db2 in BaseTable.get_known_databases()

    @pytest.mark.js_tables_sql
    def test_export(self):
        """
        Test entry export (Using Keywords, Jobs, Metadata and TimeStamps)
        :return:
        """
        gen1 = self.make_small_database()
        gen2 = self.make_small_database()
        db1 = f"{self.test_folder}/database1.db"
        self.screen_var("database", db1)

        for i, obj in enumerate(gen1):
            self.screen_var(f"testObj {i} V1", obj)
        for i, obj in enumerate(gen2):
            self.screen_var(f"testObj {i} V2", obj)

        # pylint: disable=C0200
        # I prefer not enumerate since I use i for both list_a and list_b
        for i in range(0, len(gen1)):
            assert gen1[i].flat() == gen2[i].flat()

        with BaseTable.get_session(db1, logger=CoreLogger.logger) as session:
            session.add_all(gen1)

        # 2 exists
        with BaseTable.get_session(db1, logger=CoreLogger.logger) as session:
            for i in range(0, len(gen1)):
                assert gen2[i].exists(session)

    @pytest.mark.js_tables_sql
    def test_sanitise_and_commit__added_twice_trough_multiple_session_no_update_case(
        self,
    ):
        """Test to add the same list of element twice using two session"""
        db1 = f"{self.test_folder}/database1.db"
        list_a = self.make_small_database()
        list_b = self.make_small_database()

        # Ensure that content of a, b and c are equivalent
        # pylint: disable=C0200
        # I prefer not enumerate since I use i for both list_a and list_b
        for i in range(0, len(list_a)):
            assert list_a[i].flat() == list_b[i].flat()

        # Insertion without any conflict
        with BaseTable.get_session(db1) as session:
            session.add_all(list_a)

        # Commit sanitation with collisions in existing database
        # - No error raised due to existing primary keys
        with BaseTable.get_session(db1) as session:
            session.add_all(list_b)

    @pytest.mark.js_tables_sql
    def test_sanitise_and_commit__added_twice_trough_multiple_session_update_case(
        self,
    ):
        """Test to add the same primary keys twice with different values using two session and test
        order of insertion"""
        # - No error raised due to duplicates in added primary keys using multiple sessions
        strid1 = "strid1"
        intid1 = 15
        ival1 = 55.02
        ival2 = 69.99
        db1 = f"{self.test_folder}/database.db"
        j1_a = self.TestBaseTable(
            string_id=strid1,
            value=ival1,
            integer_id=intid1,
        )
        j1_b = self.TestBaseTable(
            string_id=strid1,
            value=ival2,
            integer_id=intid1,
        )
        self.screen_var("j1_b", j1_b)
        self.screen_var("j1_a", j1_a)

        # No Error raised ?
        with BaseTable.get_session(db1) as session:
            session.add(j1_a)

        with BaseTable.get_session(db1) as session:
            session.add(j1_b)

        j1_c_1 = self.TestBaseTable(
            string_id=strid1,
            value=ival1,
            integer_id=intid1,
        )
        j1_c_2 = self.TestBaseTable(
            string_id=strid1,
            value=ival2,
            integer_id=intid1,
        )
        self.screen_var("j1_c_1", j1_c_1)
        self.screen_var("j1_c_2", j1_c_2)

        # Correctly added ?
        # The second one (j1_b / j1_c_2) should be  the one on the database
        with BaseTable.get_session(db1) as session:
            assert j1_c_1.exists(session)
            assert j1_c_2.exists(session)
            j1_d = j1_c_2.get_existing_self(session)
            self.screen_var("j1_d", j1_d)

            assert j1_d.to_dict() != j1_c_1.to_dict()
            assert j1_d.to_dict() == j1_c_2.to_dict()

    @pytest.mark.js_tables_sql
    def test_sanitise_and_commit__added_twice_no_update_case(self):
        """Test to add the same primary keys twice using one session"""
        # - No error raised due to duplicates in added primary keys using one session
        strid1 = "strid1"
        intid1 = 15
        ival1 = 55.05
        db1 = f"{self.test_folder}/database.db"
        j1_a = self.TestBaseTable(
            string_id=strid1,
            value=ival1,
            integer_id=intid1,
        )
        j1_b = self.TestBaseTable(
            string_id=strid1,
            value=ival1,
            integer_id=intid1,
        )
        self.screen_var("j1_a", j1_a)
        self.screen_var("j1_b", j1_b)

        # No Error raised ?
        with BaseTable.get_session(db1) as session:
            session.add_all([j1_a, j1_b])
        j1_c = self.TestBaseTable(
            string_id=strid1,
            value=ival1,
            integer_id=intid1,
        )
        self.screen_var("j1_c", j1_c)

        # Correctly added ?
        with BaseTable.get_session(db1) as session:
            assert j1_c.exists(session)
            j1_d = j1_c.get_existing_self(session)
            self.screen_var("j1_d", j1_d)
            assert j1_d.to_dict() == j1_c.to_dict()

    @pytest.mark.js_tables_sql
    def test_sanitise_and_commit__added_twice_update_case(self):
        """Test to add the same primary keys twice with different values using one session and test
        order of insertion"""
        # - No error raised due to duplicates in added primary keys and the
        #  entry is in the database
        strid1 = "strid1"
        ival1 = 44.02
        ival2 = 55.95
        intid1 = 99
        db1 = f"{self.test_folder}/database.db"
        j1_a = self.TestBaseTable(
            string_id=strid1,
            value=ival1,
            integer_id=intid1,
        )
        j1_b = self.TestBaseTable(
            string_id=strid1,
            value=ival2,
            integer_id=intid1,
        )
        self.screen_var("j1_a", j1_a)
        self.screen_var("j1_b", j1_b)

        # No Error raised ?
        with BaseTable.get_session(db1) as session:
            session.add_all([j1_a, j1_b])
        j1_c_1 = self.TestBaseTable(
            string_id=strid1,
            value=ival1,
            integer_id=intid1,
        )
        j1_c_2 = self.TestBaseTable(
            string_id=strid1,
            value=ival2,
            integer_id=intid1,
        )
        self.screen_var("j1_c_1", j1_c_1)
        self.screen_var("j1_c_2", j1_c_2)

        # Correctly added ?
        with BaseTable.get_session(db1) as session:
            assert j1_c_1.exists(session)
            assert j1_c_2.exists(session)
            j1_d = j1_c_2.get_existing_self(session)
            self.screen_var("j1_d", j1_d)

            # Since content in new is unordered one of the following should be true
            j1_a_has_been_selected = (
                j1_d.to_dict() == j1_c_1.to_dict()
                and j1_d.to_dict() != j1_c_2.to_dict()
            )
            j1_b_has_been_selected = (
                j1_d.to_dict() == j1_c_2.to_dict()
                and j1_d.to_dict() != j1_c_1.to_dict()
            )
            assert j1_a_has_been_selected or j1_b_has_been_selected

    def test_sanitise_and_commit__insertion_update(self):
        """Test added to ensure that updates are correctly made."""
        tbt1 = self.TestBaseTable(
            string_id = '0',
            integer_id = 0,
            value = None,
            time_stamp =None,
        )
        tbt2 = self.TestBaseTable(
            string_id = '0',
            integer_id = 0,
            value = 5,
        )
        tbt3 = self.TestBaseTable(
            string_id = '0',
            integer_id = 0,
            value = 5,
        )
        db1 = f"{self.test_folder}/database.db"
        self.screen_var("db", db1)
        self.screen_multiple_vars("tbt", tbt1, tbt2)
        self.screen_var("exist_tbt", tbt3)

        with self.TestBaseTable.get_session(db1) as session:
            session.add(tbt1)

        with self.TestBaseTable.get_session(db1) as session:
            session.add(tbt2)

        with self.TestBaseTable.get_session(db1) as session:
            result = tbt3.get_existing_self(session)
            assert result is not None
            assert result.string_id == "0"
            assert result.integer_id == 0
            assert result.value == 5


    def test_get_all(self):
        """Ensure that <get_all> returns all object with the same class as the table used."""
        db1 = f"{self.test_folder}/database.db"

        class SecondTestBaseTable(BaseTable):
            """Quicly defined table class. This Class is used to ensure that <get_all> returns only
            instances related to the class used."""

            __abstract__ = False
            __tablename__ = "SecondTestTable"
            string_id = Column(
                "strid", String, primary_key=True, nullable=False
            )

        st1 = SecondTestBaseTable(string_id="15")
        st2 = SecondTestBaseTable(string_id="Beta")
        self.screen_var("st1", st1)
        self.screen_var("st2", st2)
        db = self.make_small_database()

        with BaseTable.get_session(db1) as session:
            session.add_all([st1, st2, *db])

        with BaseTable.get_session(db1) as session:
            assert len(SecondTestBaseTable.get_all(session).all()) == 2
            assert len(self.TestBaseTable.get_all(session).all()) == len(db)

    # ===================================== #
    #                 Utils                 #
    # ===================================== #

    class TestBaseTable(BaseTable):
        """Test class used to test BaseTableForJobScrapper functionalities"""

        __abstract__ = False
        __tablename__ = "BaseTestTable"
        string_id = Column("strid", String, primary_key=True, nullable=False)
        integer_id = Column("intid", Integer, primary_key=True, nullable=False)
        value = Column(Float, nullable=True)
        time_stamp = Column(DateTime, nullable=True)

    def make_small_database(self) -> list[TestBaseTable]:
        """Generate a list of 5 TestBaseTableForJobScrapper."""
        t1 = datetime(year=1945, month=12, day=24)
        t2 = datetime(year=1946, month=1, day=12)
        return [
            self.TestBaseTable(
                string_id="id1",
                integer_id=621,
                value=47.12,
                time_stamp=t1,
            ),
            self.TestBaseTable(
                string_id="id2",
                integer_id=621,
                value=47.12,
                time_stamp=t1,
            ),
            self.TestBaseTable(
                string_id="id1",
                integer_id=622,
                value=47.12,
                time_stamp=t1,
            ),
            self.TestBaseTable(
                string_id="id2",
                integer_id=600,
                value=63.45,
                time_stamp=t2,
            ),
            self.TestBaseTable(
                string_id="id1",
                integer_id=650,
                value=47.12,
                time_stamp=t2,
            ),
        ]

    def make_one_entry(
        self, screen_name: str = "RBRFJS-1"
    ) -> TestBaseTable:
        """Generate one TestBaseTableForJobScrapper. Returns both the object and the datetime used as time_stamp."""
        obj = self.TestBaseTable(
            string_id="AnId",
            integer_id=42,
            value=63.45,
            time_stamp=NOW,
        )
        self.screen_var(screen_name, obj)
        return obj

    def make_two_identical_entries(
        self, screen_name: str = "==Entry"
    ) -> tuple[TestBaseTable, TestBaseTable]:
        """Generate two identical TestBaseTableForJobScrapper."""
        obj1 = self.TestBaseTable(
            string_id="AnId",
            integer_id=42,
            value=63.45,
            time_stamp=NOW,
        )
        obj2 = self.TestBaseTable(
            value=63.45,
            time_stamp=NOW,
            string_id="AnId",
            integer_id=42,
        )
        self.screen_var(screen_name + "1", obj1)
        self.screen_var(screen_name + "2", obj2)
        return obj1, obj2


    def make_two_equ_entries(
        self, screen_name: str = "~=Entry"
    ) -> tuple[TestBaseTable, TestBaseTable]:
        """Generate two equivalent TestBaseTableForJobScrapper."""
        obj1 = self.TestBaseTable(
            string_id="AnId",
            integer_id=42,
            value=63.45,
            time_stamp=NOW,
        )
        obj2 = self.TestBaseTable(
            value=75,
            time_stamp=NOW,
            string_id="AnId",
            integer_id=42,
        )
        self.screen_var(screen_name + "1", obj1)
        self.screen_var(screen_name + "2", obj2)
        return obj1, obj2
