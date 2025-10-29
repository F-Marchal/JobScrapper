from .base_table import BaseTableForJobScrapper
from sqlalchemy import Column, String, Float
from sqlalchemy.orm import Session

class Distances(BaseTableForJobScrapper):
    """Contains distances between one place and another place."""
    __abstract__ = False
    __tablename__ = "distances"

    reference_localisation = Column(String, primary_key=True, nullable=False)
    job_localisation = Column(String, primary_key=True, nullable=False)
    distance = Column(Float)

    @classmethod
    def get_job_associated_distances(cls, session: Session, job_localisation: str) -> list:
        return cls.get_all(session).filter_by(job_localisation=job_localisation).all()

    # job = relationship(
    #    "Jobs",
    #    primaryjoin=f"Jobs.localisation==Distances.job_localisation",
    #    back_populates="distances_from_job",
    #    viewonly=True