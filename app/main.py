from contextlib import asynccontextmanager
from csv import DictReader
from pathlib import Path

from fastapi import FastAPI

STOPS_CSV_PATH = Path(__file__).parent.parent / "data" / "stops.csv"


def load_stops() -> list[dict[str, str | float]]:
    stops: list[dict[str, str | float]] = []

    with STOPS_CSV_PATH.open(encoding="utf-8-sig") as file:
        reader = DictReader(file)

        for row in reader:
            stops.append(
                {
                    "stop_id": row["id"],
                    "stop_name": row["name"],
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                }
            )

    return stops


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.stops = load_stops()
    yield


app = FastAPI(
    title="Mock DRT Server",
    lifespan=lifespan,
)


@app.get("/stops")
def get_stops():
    return app.state.stops