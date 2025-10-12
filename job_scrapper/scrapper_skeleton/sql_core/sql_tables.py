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

# Création de la base SQLite en mémoire
engine = create_engine("sqlite:///:memory:")
_Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Ajout de 2 jobs
jobs_data = [
    Jobs(
        time_stamp=date.today(),
        origin="LinkedIn",
        localisation="Paris",
        field="IT",
        contract="CDI",
        title="Dev Python",
        url="https://test.com/job1"
    ),
    Jobs(
        time_stamp=date.today(),
        origin="Indeed",
        localisation="Lyon",
        field="IT",
        contract="CDD",
        title="Data Analyst",
        url="https://test.com/job2"
    )
]

session.add_all(jobs_data)
session.commit()

# Ajout de metadata, keywords et timestamps
for job in jobs_data:
    session.add_all([
        Metadata(url=job.url, key="source", value=job.origin),
        Metadata(url=job.url, key="location", value=job.localisation),
        Keywords(url=job.url, keyword="Python", occurrence=3),
        Keywords(url=job.url, keyword="Data", occurrence=1),
        TimeStamps(url=job.url, keyword="Python", time_stamp=date.today()),
        TimeStamps(url=job.url, keyword="Data", time_stamp=date.today())
    ])
session.commit()

# Vérification avant suppression
print("Avant suppression:")
print("Jobs:", session.query(Jobs).count())
print("Metadata:", session.query(Metadata).count())
print("Keywords:", session.query(Keywords).count())
print("TimeStamps:", session.query(TimeStamps).count())

# Suppression d'un job
job_to_delete = session.query(Jobs).filter_by(url="https://test.com/job1").first()
session.delete(job_to_delete)
session.commit()

# Vérification après suppression
print("\nAprès suppression de job1:")
print("Jobs:", session.query(Jobs).count())
print("Metadata:", session.query(Metadata).count())
print("Keywords:", session.query(Keywords).count())
print("TimeStamps:", session.query(TimeStamps).count())

# Affichage des urls restantes
remaining_jobs = session.query(Jobs).all()
print("\nURLs restantes:", [job.url for job in remaining_jobs])