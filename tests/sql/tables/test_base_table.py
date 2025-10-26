import os.path

from sql.tables import BaseTableForJobScrapper
from sqlalchemy import Column, String, Integer, Float, DateTime
from tests.conftest import BaseTest
from datetime import datetime, timedelta
from tools.logger_core import CoreLogger
import pytest


'''
   




'''
@pytest.mark.js_tables
class TestTableForJobScrapper(BaseTest):
    # ===================================== #
    #             js_tables_pyt             #
    # ===================================== #
    @pytest.mark.js_tables_pyt
    def test_get_column_using_sql_name(self):
        cusn = self.TestBaseTableForJobScrapper.get_columns_using_sql_name()
        self.screen_var("cusn", cusn)
        assert cusn["strid"] == self.TestBaseTableForJobScrapper.string_id
        assert cusn["intid"] == self.TestBaseTableForJobScrapper.integer_id
        assert cusn["value"] == self.TestBaseTableForJobScrapper.value
        assert cusn["time_stamp"] == self.TestBaseTableForJobScrapper.time_stamp

    @pytest.mark.js_tables_pyt
    def test_get_columns_using_attr_name(self):
        cuan = self.TestBaseTableForJobScrapper.get_columns_using_attr_name()
        self.screen_var("cuan", cuan)

        assert cuan["string_id"] == self.TestBaseTableForJobScrapper.string_id
        assert cuan["integer_id"] == self.TestBaseTableForJobScrapper.integer_id
        assert cuan["value"] == self.TestBaseTableForJobScrapper.value
        assert cuan["time_stamp"] == self.TestBaseTableForJobScrapper.time_stamp

    # --- get columns ---
    @pytest.mark.js_tables_pyt
    def test_get_columns(self):
        pass

    @pytest.mark.js_tables_pyt
    def test_get_pk_columns(self):
        pass

    @pytest.mark.js_tables_pyt
    def test_get_non_pk_columns(self):
        pass

    # --- to_dicts ---
    @pytest.mark.js_tables_pyt
    def test_to_dict(self):
        pass

    @pytest.mark.js_tables_pyt
    def test_to_pk_dict(self):
        pass

    @pytest.mark.js_tables_pyt
    def test_to_non_pk_dict(self):
       pass

    # --- flat ---
    @pytest.mark.js_tables_pyt
    def test_flat(self):
        pass

    @pytest.mark.js_tables_pyt
    def test_flat_non_pk(self):
        pass

    @pytest.mark.js_tables_pyt
    def test_flat_pk(self):
        pass

    # --- Get existing ---
    @pytest.mark.js_tables_pyt
    def test__eq__(self):
        pass

    # ===================================== #
    #     js_tables_sql / js_tables_pyt     #
    # ===================================== #
    @pytest.mark.js_tables_pyt
    @pytest.mark.js_tables_sql
    def test_get_existing_self(self):
        pass

    @pytest.mark.js_tables_pyt
    @pytest.mark.js_tables_sql
    def test_exists(self):
        pass

    # ===================================== #
    #             js_tables_sql             #
    # ===================================== #
    @pytest.mark.js_tables_sql
    def test_get_session(self):
        """
        Test the get_session command (and all sub commands)
        - get_known_databases
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

        with BaseTableForJobScrapper.get_session(db1):
            pass

        with BaseTableForJobScrapper.get_session(db2):
            pass

        assert os.path.exists(db1)
        assert os.path.exists(db2)

        assert db1 in BaseTableForJobScrapper.get_known_databases()
        assert db2 in BaseTableForJobScrapper.get_known_databases()

    @pytest.mark.js_tables_sql
    def test_export(self):
        """
        Test entry export (Using Keywords, Jobs, Metadata and TimeStamps)
        :return: 
        """
        gen1 = self.make_small_database()
        db1 = f"{self.test_folder}/database1.db"
        self.screen_var("database", db1)
        for i, obj in enumerate(gen1) : self.screen_var(f"testObj {i} V1", obj)

        with BaseTableForJobScrapper.get_session(db1, logger=CoreLogger.logger) as session:
            session.add_all(gen1)

        gen2 = self.make_small_database()
        for i, obj in enumerate(gen2): self.screen_var(f"testObj {i} V2", obj)

        for i in range(0, len(gen1)):
            assert gen1[i].flat() == gen2[i].flat()

        # 2 exists
        with BaseTableForJobScrapper.get_session(db1, logger=CoreLogger.logger) as session:
            for i in range(0, len(gen1)):
                assert gen2[i].exists(session)

    @pytest.mark.js_tables_sql
    def test_sanitise_and_commit__added_twice_trough_multiple_session_no_update_case(self):
        db1 = f"{self.test_folder}/database1.db"
        list_a = self.make_small_database()
        list_b =  self.make_small_database()

        # Ensure that content of a, b and c are equivalent
        for i in range(0, len(list_a)):
            assert list_a[i].flat() == list_b[i].flat()

        # Insertion without any conflict
        with BaseTableForJobScrapper.get_session(db1) as session:
            session.add_all(list_a)

        # Commit sanitation with collisions in existing database
        # - No error raised due to existing primary keys
        with BaseTableForJobScrapper.get_session(db1) as session:
            session.add_all(list_b)

    @pytest.mark.js_tables_sql
    def test_sanitise_and_commit__added_twice_trough_multiple_session_update_case(self):
        # - No error raised due to duplicates in added primary keys using multiple sessions
        strid1 = "strid1"
        intid1 = 15
        ival1 = 55.02
        ival2 = 69.99
        db1 = f"{self.test_folder}/database.db"
        j1_a = self.TestBaseTableForJobScrapper(
            string_id=strid1,
            value=ival1,
            integer_id=intid1,
        )
        j1_b = self.TestBaseTableForJobScrapper(
            string_id=strid1,
            value=ival2,
            integer_id=intid1,
        )
        self.screen_var("j1_b", j1_b)
        self.screen_var("j1_a", j1_a)


        # No Error raised ?
        with BaseTableForJobScrapper.get_session(db1) as session:
            session.add(j1_a)

        with BaseTableForJobScrapper.get_session(db1) as session:
            session.add(j1_b)

        j1_c_1 = self.TestBaseTableForJobScrapper(
            string_id=strid1,
            value=ival1,
            integer_id=intid1,
        )
        j1_c_2 = self.TestBaseTableForJobScrapper(
            string_id=strid1,
            value=ival2,
            integer_id=intid1,
        )
        self.screen_var("j1_c_1", j1_c_1)
        self.screen_var("j1_c_2", j1_c_2)

        # Correctly added ?
        # The first (j1_a / j1_c_1) one should be the one on the database
        with BaseTableForJobScrapper.get_session(db1) as session:
            assert j1_c_1.exists(session)
            assert j1_c_2.exists(session)
            j1_d = j1_c_2.get_existing_self(session)
            self.screen_var("j1_d", j1_d)

            assert j1_d.to_dict() != j1_c_1.to_dict()
            assert j1_d.to_dict() == j1_c_2.to_dict()

    @pytest.mark.js_tables_sql
    def test_sanitise_and_commit__added_twice_no_update_case(self):
        # - No error raised due to duplicates in added primary keys using one session
        strid1 = "strid1"
        intid1 = 15
        ival1 = 55.05
        db1 = f"{self.test_folder}/database.db"
        j1_a = self.TestBaseTableForJobScrapper(
            string_id=strid1,
            value=ival1,
            integer_id=intid1,
        )
        j1_b = self.TestBaseTableForJobScrapper(
            string_id=strid1,
            value=ival1,
            integer_id=intid1,
        )
        self.screen_var("j1_a", j1_a)
        self.screen_var("j1_b", j1_b)

        # No Error raised ?
        with BaseTableForJobScrapper.get_session(db1) as session:
            session.add_all([j1_a, j1_b])
        j1_c = self.TestBaseTableForJobScrapper(
            string_id=strid1,
            value=ival1,
            integer_id=intid1,
        )
        self.screen_var("j1_c", j1_c)

        # Correctly added ?
        with BaseTableForJobScrapper.get_session(db1) as session:
            assert j1_c.exists(session)
            j1_d = j1_c.get_existing_self(session)
            self.screen_var("j1_d", j1_d)
            assert j1_d.to_dict() == j1_c.to_dict()

    @pytest.mark.js_tables_sql
    def test_sanitise_and_commit__added_twice_update_case(self):
        # - No error raised due to duplicates in added primary keys and the
        #  entry is in the database
        strid1 = "strid1"
        ival1 = 44.02
        ival2 = 55.95
        intid1=99
        db1 = f"{self.test_folder}/database.db"
        j1_a = self.TestBaseTableForJobScrapper(
            string_id=strid1,
            value=ival1,
            integer_id=intid1,

        )
        j1_b = self.TestBaseTableForJobScrapper(
            string_id=strid1,
            value=ival2,
            integer_id=intid1,
        )
        self.screen_var("j1_a", j1_a)
        self.screen_var("j1_b", j1_b)

        # No Error raised ?
        with BaseTableForJobScrapper.get_session(db1) as session:
            session.add_all([j1_a, j1_b])
        j1_c_1 = self.TestBaseTableForJobScrapper(
            string_id=strid1,
            value=ival1,
            integer_id=intid1,
        )
        j1_c_2 = self.TestBaseTableForJobScrapper(
            string_id=strid1,
            value=ival2,
            integer_id=intid1,
        )
        self.screen_var("j1_c_1", j1_c_1)
        self.screen_var("j1_c_2", j1_c_2)

        # Correctly added ?
        # The first (j1_a / j1_c_1) one should be the one on the database
        with BaseTableForJobScrapper.get_session(db1) as session:
            assert j1_c_1.exists(session)
            assert j1_c_2.exists(session)
            j1_d = j1_c_2.get_existing_self(session)
            self.screen_var("j1_d", j1_d)

            assert j1_d.to_dict() == j1_c_1.to_dict()
            assert j1_d.to_dict() != j1_c_2.to_dict()

        # TODO: Add_all list of unknown primary keys with duplicates that have some values modified from original
        # TODO: Add_all list of known primary keys with some values modified from original
        # TODO: All of the above at once !


    # ===================================== #
    #                 Utils                 #
    # ===================================== #

    class TestBaseTableForJobScrapper(BaseTableForJobScrapper):
        __abstract__ = False
        __tablename__ = "BaseTestTable"
        string_id = Column("strid", String, primary_key=True, nullable=False)
        integer_id = Column("intid", Integer, primary_key=True, nullable=False)
        value = Column(Float, nullable=True)
        time_stamp = Column(DateTime, nullable=True)

    def make_small_database(self):
        t1 = datetime(
            year=1945,
            month=12,
            day=24
        )
        t2 = datetime(
            year=1946,
            month=1,
            day=12
        )
        return [
            self.TestBaseTableForJobScrapper(
                string_id="id1",
                integer_id=621,
                value=47.12,
                time_stamp=t1,
            ),
            self.TestBaseTableForJobScrapper(
                string_id="id2",
                integer_id=621,
                value=47.12,
                time_stamp=t1,
            ),
            self.TestBaseTableForJobScrapper(
                string_id="id1",
                integer_id=622,
                value=47.12,
                time_stamp=t1,
            ),
            self.TestBaseTableForJobScrapper(
                string_id="id2",
                integer_id=600,
                value=63.45,
                time_stamp=t2,
            ),
            self.TestBaseTableForJobScrapper(
                string_id="id1",
                integer_id=621,
                value=47.12,
                time_stamp=t2,
            )
        ]

    def make_one_entry(self):
        now = datetime.now()
        return self.TestBaseTableForJobScrapper(
            string_id="AnId",
            integer_id=42,
            value=63.45,
            time_stamp=now,
        ),now