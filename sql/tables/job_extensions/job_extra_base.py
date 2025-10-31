from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import Query, Session

from sql.tables.base_table import BaseTable
from sql.tables.jobs import Jobs


class JobExtraBase(BaseTable):
    """Abstract class use to extend data attached to Jobs. Each table that inherit JobExtraBase uses Job.Url
    as primary key and are deleted when the attached jobs is deleted.

    ASSOCIATION ARE DEFINED IN JOBS AND IN SUBCLASS"""

    __abstract__ = True

    url = Column(
        String,
        ForeignKey(f"{Jobs.__tablename__}.url", ondelete="CASCADE"),
        primary_key=True,
    )

    @classmethod
    def get_for_job(cls, session: Session, url: str | Jobs) -> Query:
        """
        Returns als cls entries attached to a job using its url
        :param session: A session linked to a database
        :param url: An url or a Jobs Object
        :return: A query object
        """
        raise NotImplementedError
