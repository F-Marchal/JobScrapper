from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship, validates

from .base_table import BaseTable


class Jobs(BaseTable):
    """
    Main table. Contains main information related to jobs offers :
    contract, field, url ...
    """
    DEFAULT_LOCALISATION = "Unknown"

    __abstract__ = False
    __tablename__ = "jobs"

    # Table columns
    contract = Column(String, nullable=True)
    field = Column(String, nullable=True)
    localisation = Column(
        String,
        ForeignKey(
            "places.localisation",
            ondelete="RESTRICT" # Cannot delete a Place if any Job points to it.
        ),
        nullable=False,
        default=DEFAULT_LOCALISATION
    )
    origin = Column(String, nullable=True)
    title = Column(String, nullable=True)
    url = Column(String, primary_key=True, nullable=False)

    # time_stamp = Column(Date, nullable=False)

    # Table relationships
    # Relations dynamiques
    metadata_entries = relationship(
        "Metadata",
        back_populates="main_entry",
        cascade="all, delete-orphan",
        lazy="dynamic",  # Gives a query object instead of a list when
                         # job = session.get(Jobs, "url_du_job") ; job.metadata_entries
    )
    keywords_entries = relationship(
        "Keywords",
        back_populates="main_entry",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    timestamps_entries = relationship(
        "TimeStamps",
        back_populates="main_entry",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    places_entry = relationship(
        "Places",
        back_populates="jobs_entry"
    )

    @validates("localisation")
    def _validate_localisation(self, key, value):
        return self.format_localisation(value)

    @staticmethod
    def format_localisation(string: str) -> str:
        """Format localisation column"""
        return string.strip().title()