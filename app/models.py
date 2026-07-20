from enum import Enum

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VehicleStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    DISPATCHED = "DISPATCHED"


class Stop(Base):
    __tablename__ = "stops"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    nearest_stop_id: Mapped[str] = mapped_column(
        ForeignKey("stops.id"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String,
        default=VehicleStatus.AVAILABLE.value,
        nullable=False,
    )

    current_call_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )