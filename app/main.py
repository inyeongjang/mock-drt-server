import random
from contextlib import asynccontextmanager
from csv import DictReader
from pathlib import Path

from math import asin, cos, radians, sin, sqrt
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine, get_db
from app.models import Call, CallStatus, Stop, Vehicle, VehicleStatus
from app.schemas import CallCreateRequest, CallCreateResponse


STOPS_CSV_PATH = Path(__file__).parent.parent / "data" / "stops.csv"
VEHICLE_COUNT = 3
VEHICLE_SPEED_KMH = 30.0


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


def calculate_distance_km(
    latitude1: float,
    longitude1: float,
    latitude2: float,
    longitude2: float,
) -> float:
    earth_radius_km = 6371.0

    lat1 = radians(latitude1)
    lon1 = radians(longitude1)
    lat2 = radians(latitude2)
    lon2 = radians(longitude2)

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    haversine = (
        sin(delta_lat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    )

    return 2 * earth_radius_km * asin(sqrt(haversine))


def calculate_eta_seconds(distance_km: float) -> int:
    travel_hours = distance_km / VEHICLE_SPEED_KMH
    travel_seconds = int(travel_hours * 3600)

    return max(travel_seconds, 1)


def find_nearest_available_vehicle(
    db: Session,
    departure_stop: Stop,
) -> tuple[Vehicle, float] | None:
    vehicles = db.scalars(
        select(Vehicle).where(
            Vehicle.status == VehicleStatus.AVAILABLE.value
        )
    ).all()

    if not vehicles:
        return None

    vehicle_distances = [
        (
            vehicle,
            calculate_distance_km(
                vehicle.latitude,
                vehicle.longitude,
                departure_stop.latitude,
                departure_stop.longitude,
            ),
        )
        for vehicle in vehicles
    ]

    return min(vehicle_distances, key=lambda item: item[1])


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

@app.post(
    "/calls",
    response_model=CallCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_call(
    request: CallCreateRequest,
    db: Session = Depends(get_db),
):
    if request.departure_stop_id == request.arrival_stop_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="출발 정류장과 도착 정류장은 달라야 합니다.",
        )

    departure_stop = db.get(Stop, request.departure_stop_id)

    if departure_stop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="출발 정류장을 찾을 수 없습니다.",
        )

    arrival_stop = db.get(Stop, request.arrival_stop_id)

    if arrival_stop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="도착 정류장을 찾을 수 없습니다.",
        )

    nearest_result = find_nearest_available_vehicle(
        db,
        departure_stop,
    )

    if nearest_result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="현재 이용 가능한 차량이 없습니다.",
        )

    vehicle, distance_km = nearest_result
    call_id = f"CALL-{uuid4().hex[:8].upper()}"
    estimated_arrival_seconds = calculate_eta_seconds(distance_km)

    call = Call(
        id=call_id,
        vehicle_id=vehicle.id,
        departure_stop_id=departure_stop.id,
        arrival_stop_id=arrival_stop.id,
        status=CallStatus.DISPATCHED.value,
        estimated_arrival_seconds=estimated_arrival_seconds,
    )

    vehicle.status = VehicleStatus.DISPATCHED.value
    vehicle.current_call_id = call_id

    db.add(call)
    db.commit()
    db.refresh(call)
    db.refresh(vehicle)

    return CallCreateResponse(
        call_id=call.id,
        vehicle_id=vehicle.id,
        call_status=call.status,
        estimated_arrival_seconds=call.estimated_arrival_seconds,
        vehicle_latitude=vehicle.latitude,
        vehicle_longitude=vehicle.longitude,
        nearest_stop_id=vehicle.nearest_stop_id,
    )