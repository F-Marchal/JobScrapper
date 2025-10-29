from sql.tables.base_table import BaseTable
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sql.tables.jobs import Jobs
from sqlalchemy.orm import Session

class TimeStamps(BaseTable):
    """Time stamps attached to a job offer."""
    __abstract__ = False
    __tablename__ = "timestamps"

    url = Column(String, ForeignKey(f"{Jobs.__tablename__}.url", ondelete="CASCADE"), primary_key=True)
    label = Column(String, primary_key=True, nullable=False)
    time_stamp =  Column(DateTime, nullable=False)

    main_entry = relationship("Jobs", back_populates="timestamps_entries", passive_deletes=True)

    @classmethod
    def get_job_associated_time_stamps(cls, session: Session, url: str) -> list:
        """Get a list of all time stamps attached to a url."""
        return cls.get_all(session).filter_by(url=url).all()