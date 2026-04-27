from fastapi import APIRouter
from routes.upload import vehicle_profiles

router = APIRouter()

@router.get("/vehicle/{filename}")
def get_vehicle(filename: str):
    return vehicle_profiles.get(filename, {})