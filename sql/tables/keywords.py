from .base_table import BaseTableForJobScrapper
from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.orm import relationship
from .jobs import Jobs
from sqlalchemy.orm import Session

class Keywords(BaseTableForJobScrapper):
    """Table that contain the number of occurrences of a word (and aliases) inside
     a job offer"""
    __abstract__ = False
    __tablename__ = "keywords"

    url = Column(String, ForeignKey(f"{Jobs.__tablename__}.url", ondelete="CASCADE"), primary_key=True)
    keyword = Column(String, primary_key=True, nullable=False)
    occurrence = Column(Integer, nullable=True)

    main_entry = relationship("Jobs", back_populates="keywords_entries", passive_deletes=True)

    @classmethod
    def get_job_associated_keywords(cls, session: Session, url: str) -> list:
        """Get keywords count associated to a url."""
        return cls.get_all(session).filter_by(url=url).all()
