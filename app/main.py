import random
from contextlib import asynccontextmanager
from csv import DictReader
from pathlib import Path

from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine, get_db
from app.models import Stop, Vehicle, VehicleStatus

STOPS_CSV_PATH = Path(__file__).parent.parent / "data" / "stops.csv"
VEHICLE_COUNT = 3


def load_stops_from_csv() -> list[dict[str, str | float]]:
    stops: list[dict[str, str | float]] = []

    with STOPS_CSV_PATH.open(encoding="utf-8-sig") as file:
        reader = DictReader(file)

        for row in reader:
            stops.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                }
            )

    return stops


def initialize_stops(db: Session) -> None:
    existing_stop = db.scalar(select(Stop).limit(1))

    if existing_stop is not None:
        return

    stop_data = load_stops_from_csv()

    for data in stop_data:
        db.add(
            Stop(
                id=str(data["id"]),
                name=str(data["name"]),
                latitude=float(data["latitude"]),
                longitude=float(data["longitude"]),
            )
        )

    db.commit()


def initialize_vehicles(db: Session) -> None:
    existing_vehicle = db.scalar(select(Vehicle).limit(1))

    if existing_vehicle is not None:
        return

    stops = list(db.scalars(select(Stop)).all())

    if not stops:
        raise RuntimeError("차량을 배치할 정류장이 없습니다.")

    selected_stops = random.choices(stops, k=VEHICLE_COUNT)

    for index, stop in enumerate(selected_stops, start=1):
        db.add(
            Vehicle(
                id=f"VEHICLE-{index:03d}",
                latitude=stop.latitude,
                longitude=stop.longitude,
                nearest_stop_id=stop.id,
                status=VehicleStatus.AVAILABLE.value,
                current_call_id=None,
            )
        )

    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        initialize_stops(db)
        initialize_vehicles(db)

    yield


app = FastAPI(
    title="Mock DRT Server",
    lifespan=lifespan,
)


@app.get("/stops")
def get_stops(db: Session = Depends(get_db)):
    stops = db.scalars(select(Stop)).all()

    return [
        {
            "stop_id": stop.id,
            "stop_name": stop.name,
            "latitude": stop.latitude,
            "longitude": stop.longitude,
        }
        for stop in stops
    ]


@app.get("/vehicles")
def get_vehicles(db: Session = Depends(get_db)):
    vehicles = db.scalars(select(Vehicle)).all()

    return [
        {
            "vehicle_id": vehicle.id,
            "latitude": vehicle.latitude,
            "longitude": vehicle.longitude,
            "nearest_stop_id": vehicle.nearest_stop_id,
            "status": vehicle.status,
            "current_call_id": vehicle.current_call_id,
        }
        for vehicle in vehicles
    ]