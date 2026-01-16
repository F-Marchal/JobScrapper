from sqlalchemy import Column, String, DateTime

from .base_table import BaseTable


class ArchivedJobs(BaseTable):
    __abstract__ = False
    __tablename__ = "ArchivedJobs"
    url = Column(String, primary_key=True, nullable=False)
    when = Column(DateTime, nullable=True)
    last_sighting = Column(DateTime, nullable=True)