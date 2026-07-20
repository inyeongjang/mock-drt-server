from pydantic import BaseModel


class CallCreateRequest(BaseModel):
    departure_stop_id: str
    arrival_stop_id: str


class CallCreateResponse(BaseModel):
    call_id: str
    vehicle_id: str
    call_status: str
    estimated_arrival_seconds: int
    vehicle_latitude: float
    vehicle_longitude: float
    nearest_stop_id: str


class CallStatusResponse(BaseModel):
    call_id: str
    vehicle_id: str
    departure_stop_id: str
    arrival_stop_id: str
    call_status: str
    estimated_arrival_seconds: int
    vehicle_latitude: float
    vehicle_longitude: float
    nearest_stop_id: str