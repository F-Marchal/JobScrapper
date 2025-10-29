from .base_table import BaseTableForJobScrapper
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from .jobs import Jobs
from sqlalchemy.orm import Session

class Metadata(BaseTableForJobScrapper):
    """Table that attach metadata to job offer E.g : Everything
    that does not fit inside other table / random information"""
    __abstract__ = False
    __tablename__ = "metadata"

    # Table columns
    url = Column(String, ForeignKey(f"{Jobs.__tablename__}.url", ondelete="CASCADE"), primary_key=True)
    key = Column(String, primary_key=True, nullable=False)
    value = Column(String, nullable=False)

    # Table relationships
    main_entry = relationship("Jobs", back_populates="metadata_entries", passive_deletes=True)

    @classmethod
    def get_associated_metadata(cls, session: Session, url: str) -> list:
        """Get metadata associated to an url"""
        return cls.get_all(session).filter_by(url=url).all()
