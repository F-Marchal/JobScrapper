from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship, validates, Session

from .base_table import BaseTable
from .archived import ArchivedJobs

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

    def transfer_to_another_database(
            self,
            initial_database: Session,
            target_database: Session,
    ):
        existing_self = self.get_existing_self(
            session=initial_database,
            include_session=True,
            include_database=True,
            strict=True,
        )
        if existing_self is None:
            raise KeyError(
                f"Unable to transfer {self} from '{initial_database}' to '{target_database}'.\n"
                f"{self} is not inside '{initial_database}'."
            )

        metadata_entries = list(existing_self.metadata_entries)
        keywords_entries = list(existing_self.keywords_entries)
        keyword_version_entries = [k.version_entry for k in keywords_entries]
        keyword_regex_entries = []
        for v in keyword_version_entries:
            keyword_regex_entries.extend(list(v.regex_entries))

        timestamps_entries = list(existing_self.timestamps_entries)
        places_entry = existing_self.places_entry

        configuration_entries = [ # All entries related to self that can be related to other entries
            places_entry,
            *keyword_version_entries,
            *keyword_regex_entries,
        ]

        core_entries = [ # All entries strictly related to self.
            existing_self,
            *keywords_entries,
            *metadata_entries,
            *timestamps_entries,
        ]

        for entry in [*configuration_entries, *core_entries]:
            target_database.merge(entry)

        for entry in core_entries:
            initial_database.delete(entry)

    def archive(
            self,
            initial_database: Session,
            target_database: Session,
    ):
        self.transfer_to_another_database(
            initial_database,
            target_database
        )

        # Save that 'self' has been archived :
        initial_database.add(
            ArchivedJobs(url=self.url)
        )

        # Remove potential archive mentions the target database
        for old_archive in target_database.query(
            ArchivedJobs
        ).filter(
            ArchivedJobs.url == self.url
        ).all():
            target_database.delete(old_archive)
