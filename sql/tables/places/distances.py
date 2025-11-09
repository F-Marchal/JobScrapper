from sqlalchemy import Column, Float, String
from sqlalchemy.orm import Session

from sql.tables.base_table import BaseTable


class Distances(BaseTable):
    """Contains distances between one place and another place."""

    __abstract__ = False
    __tablename__ = "distances"

    reference_localisation = Column(String, primary_key=True, nullable=False)
    job_localisation = Column(String, primary_key=True, nullable=False)
    distance = Column(Float, nullable=True)

    @classmethod
    def get_job_associated_distances(
        cls, session: Session, job_localisation: str
    ) -> list:
        """Returns al distances associated to a <job_localisation>"""
        return (
            cls.get_all(session)
            .filter_by(job_localisation=job_localisation)
            .all()
        )

    # job = relationship(
    #    "Jobs",
    #    primaryjoin=f"Jobs.localisation==Distances.job_localisation",
    #    back_populates="distances_from_job",
    #    viewonly=True
