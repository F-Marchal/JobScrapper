from .job_extra_base import JobExtraBase, Jobs
from sqlalchemy import Column, String
from sqlalchemy.orm import Session, Query, relationship

class Metadata(JobExtraBase):
    """Table that attach metadata to job offer E.g : Everything
    that does not fit inside other table / random information"""
    __abstract__ = False
    __tablename__ = "metadata"

    # Table columns
    # url = Column(String, ForeignKey(f"{Jobs.__tablename__}.url", ondelete="CASCADE"), primary_key=True)
    key = Column(String, primary_key=True, nullable=False)
    value = Column(String, nullable=False)

    # Table relationships
    main_entry = relationship("Jobs", back_populates="metadata_entries", passive_deletes=True)

    @classmethod
    def get_for_job(cls, session: Session, url: str | Jobs) -> Query:
        """Get metadata associated to a url"""
        true_url = url.url if isinstance(url, Jobs) else url
        return cls.get_all(session).filter_by(url=true_url)

