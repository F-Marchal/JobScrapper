from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Query, Session, relationship

from .job_extra_base import JobExtraBase, Jobs


class Keywords(JobExtraBase):
    """Table that contain the number of occurrences of a word (and aliases) inside
    a job offer"""

    __abstract__ = False
    __tablename__ = "keywords"

    # url = Column(String, ForeignKey(f"{Jobs.__tablename__}.url", ondelete="CASCADE"), primary_key=True)
    keyword = Column(String, primary_key=True, nullable=False)
    occurrence = Column(Integer, nullable=True)

    main_entry = relationship(
        "Jobs", back_populates="keywords_entries", passive_deletes=True
    )

    @classmethod
    def get_for_job(cls, session: Session, url: str | Jobs) -> Query:
        """Get keywords count associated to a url."""
        true_url = url.url if isinstance(url, Jobs) else url
        return cls.get_all(session).filter_by(url=true_url)
