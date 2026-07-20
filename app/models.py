from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VehicleStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    DISPATCHED = "DISPATCHED"


class CallStatus(str, Enum):
    DISPATCHED = "DISPATCHED"
    APPROACHING = "APPROACHING"
    ARRIVED = "ARRIVED"
    IN_SERVICE = "IN_SERVICE"
    COMPLETED = "COMPLETED"


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


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[str] = mapped_column(String, primary_key=True)

    vehicle_id: Mapped[str] = mapped_column(
        ForeignKey("vehicles.id"),
        nullable=False,
    )

    departure_stop_id: Mapped[str] = mapped_column(
        ForeignKey("stops.id"),
        nullable=False,
    )

    arrival_stop_id: Mapped[str] = mapped_column(
        ForeignKey("stops.id"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String,
        default=CallStatus.DISPATCHED.value,
        nullable=False,
    )

    estimated_arrival_seconds: Mapped[int] = mapped_column(
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )