from sqlalchemy import create_engine, Column, Integer, String, select
from sqlalchemy.orm import declarative_base, Session
from contextlib import contextmanager
Base = declarative_base()


class StringTable(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)

    @staticmethod
    @contextmanager
    def get_session(path:str=":memory:"):
        engine = create_engine(f"sqlite:///{path}")  # echo=True pour voir le SQL
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            session.add_all([
                StringTable(name="Hello world"),
            ])
            session.commit()

        with Session(engine) as session:
            yield session

