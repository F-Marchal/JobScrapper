from sqlalchemy import Column, Float, String

from sql.tables.base_table import BaseTable


class Places(BaseTable):
    """Contains a number of reference places coordinates."""

    __abstract__ = False
    __tablename__ = "places"

    localisation = Column(String, primary_key=True, nullable=False)
    longitude = Column(Float, nullable=True)
    latitude = Column(Float, nullable=True)

    @property
    def lat(self) -> float | None:
        return getattr(self, "latitude")

    @property
    def long(self) -> float | None:
        return getattr(self, "longitude")

    @property
    def coord(self) -> tuple[float | None, float | None]:
        return self.lat, self.long

    def is_computable(self) -> bool:
        return self.lat is not None and self.long is not None
