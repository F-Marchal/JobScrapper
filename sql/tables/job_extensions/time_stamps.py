from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import Query, Session, relationship

from .job_extra_base import JobExtraBase, Jobs


class TimeStamps(JobExtraBase):
    """Time stamps attached to a job offer."""

    __abstract__ = False
    __tablename__ = "timestamps"

    # url = Column(String, ForeignKey(f"{Jobs.__tablename__}.url", ondelete="CASCADE"), primary_key=True)
    label = Column(String, primary_key=True, nullable=False)
    time_stamp = Column(DateTime, nullable=False)

    main_entry = relationship(
        "Jobs", back_populates="timestamps_entries", passive_deletes=True
    )

    @classmethod
    def get_for_job(cls, session: Session, url: str | Jobs) -> Query:
        """Get a Query of all time stamps attached to a url."""
        true_url = url.url if isinstance(url, Jobs) else url
        return cls.get_all(session).filter_by(url=true_url)
