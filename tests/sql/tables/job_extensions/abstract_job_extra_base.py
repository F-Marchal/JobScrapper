
from typing import Any, Type

import pytest

from sql.tables.job_extensions.job_extra_base import JobExtraBase
from sql.tables.places.places import Places
from sql.tables.jobs import Jobs
from sql.tables.places.places import Places
from tests.conftest import BaseTest


@pytest.mark.js_tables
class TestJobExtraBase(BaseTest):
    """Ensure that Distances table works as intended"""

    __tested_class__: Type[JobExtraBase] | None = None
    job_entry_name: None | str = None
    db_comp1: dict[str, Any] = {}
    db_comp2: dict[str, Any] = {}
    db_comp3: dict[str, Any] = {}

    def standard_db_path(self):
        """Returns database path."""
        return  f"{self.test_folder}/database.db"

    def test_get_job_associated_time_stamps(self):
        """Test that <get_job_associated_time_stamps> works as intended"""
        if self.__tested_class__ is None:
            self.log("No testsing class defined.")
            return

        db1 = self.standard_db_path()
        with Jobs.get_session(db1) as session:
            session.add_all(self.make_small_database())

        with Jobs.get_session(db1) as session:
            assert 2 == len(
                self.__tested_class__.get_for_job(session, "Alpha").all()
            )
            assert 1 == len(
                self.__tested_class__.get_for_job(session, "Beta").all()
            )

    def test_job_delete_cascade(self):
        """Ensure that the delete cascade works."""
        if self.__tested_class__ is None:
            self.log("No testsing class defined.")
            return

        db_path = f"{self.test_folder}/database.db"
        db = self.make_small_database()

        ref_job = db[1]
        ref_url = ref_job.url

        # Add database
        with Jobs.get_session(db_path) as session:
            session.add_all(db)

        # Delete one element to see if delete cascade works
        with Jobs.get_session(db_path) as session:
            number_of_element = len(
                self.__tested_class__.get_all(session).all()
            )
            number_of_element_associated_to_url = len(
                self.__tested_class__.get_for_job(session, url=ref_url).all()
            )
            session.delete(ref_job)

        # Test if cascade delete works as intended
        with Jobs.get_session(db_path) as session:
            assert (
                len(self.__tested_class__.get_all(session).all())
                == number_of_element - number_of_element_associated_to_url
            )

    def test_relationship(self):
        """Ensure reciprocity of relationship between Jobs and JobEtraBase"""
        db1 = self.standard_db_path()
        if self.__tested_class__ is None:
            self.log("No testsing class defined.")
            return

        with JobExtraBase.get_session(db1) as session:
            session.add_all(self.make_small_database())

        with Jobs.get_session(db1) as session:
            job_alpha = session.get(Jobs, "Alpha")
            job_beta = session.get(Jobs, "Beta")
            # number_of_element = len(self.__tested_class__.get_all(session).all())
            number_of_element_associated_to_alpha = len(
                self.__tested_class__.get_for_job(session, url=job_alpha).all()
            )
            number_of_element_associated_to_beta = len(
                self.__tested_class__.get_for_job(session, url=job_beta).all()
            )
            alpha_obj_list = (
                self.__tested_class__.get_all(session)
                .filter_by(url="Alpha")
                .all()
            )

            assert len(alpha_obj_list) > 0
            self.screen_multiple_vars("alpha_obj", *alpha_obj_list)
            for obj in alpha_obj_list:
                assert obj.main_entry.url == "Alpha"

            assert (
                len(getattr(job_alpha, self.job_entry_name).all())
                == number_of_element_associated_to_alpha
            )
            assert (
                len(getattr(job_beta, self.job_entry_name).all())
                == number_of_element_associated_to_beta
            )

    # Utils
    def test_make_small_database(self):
        """Ensure that make_small_database keep the same format across inheritance"""
        if self.__tested_class__ is None:
            self.log("No testsing class defined.")
            return

        j1, j2, ob1, ob2, ob3 = self.make_small_database()

        assert j1.url == ob1.url
        assert j1.url == ob2.url
        assert j2.url == ob3.url

        # Ensure that jobs can be added to database
        with Jobs.get_session(self.standard_db_path(), logger=self.icl.logger) as session:
            session.add_all([j1, j2])

        # ensure that ob can be added to database
        with Jobs.get_session(self.standard_db_path(), logger=self.icl.logger) as session:
            session.add_all([ob1, ob2, ob3])

    def test_missing__tested_class__(self):
        """Ensure that __tested_class__ is initialised in subclass"""
        assert (
            # pylint: disable=C0123
            # I can not use isinstance, I need to ensure that type are exactly the same, not substances.
            self.__tested_class__ is not None
            or type(self) == TestJobExtraBase
        )

    def test_missing_relationship(self):
        """Test that relationship works in both side."""
        if self.__tested_class__ is None:
            self.log("No testsing class defined.")
            return

        if self.__tested_class__:
            assert self.job_entry_name
            # Should not be failed
            getattr(
                self.__tested_class__, "main_entry"
            )  # When failed : Missing main_entry relationship
            getattr(
                Jobs, self.job_entry_name
            )  # When failed : wrong job_entry_name / missing job entry name

    def make_small_database(
        self, screen_prefix: str = ""
    ) -> tuple[Jobs, Jobs, JobExtraBase, JobExtraBase, JobExtraBase]:
        """Make a small database for test purposes."""
        if self.__tested_class__ is None:
            self.log("No tested class defined.")
            raise NotImplementedError()

        with Places.get_session(self.standard_db_path(), logger=self.icl.logger) as session:
            p1 = Places(
                localisation=Jobs.DEFAULT_LOCALISATION,
                longitude=None,
                latitude=None,
            )
            session.add(p1)

        j1 = Jobs(url="Alpha", localisation=Jobs.DEFAULT_LOCALISATION)
        j2 = Jobs(url="Beta", localisation=Jobs.DEFAULT_LOCALISATION)

        # pylint: disable=E1102:
        # If typing is respected, __tested_class__ is either None (NotImplementedError)
        # or callable
        ob1 = self.__tested_class__(url="Alpha", **self.db_comp1)
        ob2 = self.__tested_class__(url="Alpha", **self.db_comp2)
        ob3 = self.__tested_class__(url="Beta", **self.db_comp3)

        self.screen_multiple_vars(screen_prefix + "job", j1, j2)
        self.screen_multiple_vars(screen_prefix + "obj", ob1, ob2, ob3)

        return j1, j2, ob1, ob2, ob3
