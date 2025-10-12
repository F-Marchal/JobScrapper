from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, String, Date, Integer, Float, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import date

_Base = declarative_base()

class BaseTableForJobScrapper(_Base):
    __abstract__ = True

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Jobs(BaseTableForJobScrapper):
    __tablename__ = "jobs"

    # Table columns
    contract = Column(String)
    field = Column(String)
    localisation = Column(String)
    origin = Column(String)
    title = Column(String)
    url = Column(String, primary_key=True)

    # time_stamp = Column(Date, nullable=False)

    # Table relationships
    # Relations dynamiques
    metadata_entries = relationship(
        "Metadata",
        back_populates="main_entry",
        cascade="all, delete-orphan",
        lazy='dynamic' # Gives a query object instead of a list when job = session.get(Jobs, "url_du_job") ; job.metadata_entries
    )
    keywords_entries = relationship(
        "Keywords",
        back_populates="main_entry",
        cascade="all, delete-orphan",
        lazy='dynamic'
    )
    timestamps_entries = relationship(
        "TimeStamps",
        back_populates="main_entry",
        cascade="all, delete-orphan",
        lazy='dynamic'
    )

    # Ease requests
    distances_from_job = relationship(
        "Distances",
        primaryjoin="Jobs.localisation==Distances.job_localisation",
        back_populates="job",
        lazy='dynamic',  # important pour filtrer avec .filter()
        viewonly=True
    )

class Metadata(BaseTableForJobScrapper):
    __tablename__ = "metadata"

    # Table columns
    url = Column(String, ForeignKey(f"{Jobs.__tablename__}.url", ondelete="CASCADE"), primary_key=True)
    key = Column(String, primary_key=True, nullable=False)
    value = Column(String, nullable=False)

    # Table relationships
    main_entry = relationship("Jobs", back_populates="metadata_entries", passive_deletes=True)

class Keywords(BaseTableForJobScrapper):
    __tablename__ = "keywords"

    url = Column(String, ForeignKey(f"{Jobs.__tablename__}.url", ondelete="CASCADE"), primary_key=True)
    keyword = Column(String, primary_key=True, nullable=False)
    occurrence = Column(Integer)

    main_entry = relationship("Jobs", back_populates="keywords_entries", passive_deletes=True)

class TimeStamps(BaseTableForJobScrapper):
    __tablename__ = "timestamps"

    url = Column(String, ForeignKey(f"{Jobs.__tablename__}.url", ondelete="CASCADE"), primary_key=True)
    keyword = Column(String, primary_key=True, nullable=False)
    time_stamp = Column(Date, nullable=False)

    main_entry = relationship("Jobs", back_populates="timestamps_entries", passive_deletes=True)

class Distances(BaseTableForJobScrapper):
    __tablename__ = "distances"

    reference_localisation = Column(String, primary_key=True, nullable=False)
    job_localisation = Column(String, primary_key=True, nullable=False)
    distance = Column(Float)

    job = relationship(
        "Jobs",
        primaryjoin=f"Jobs.localisation==Distances.job_localisation",
        back_populates="distances_from_job",
        viewonly=True
    )
