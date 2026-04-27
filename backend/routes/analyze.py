from fastapi import APIRouter
from services.analyzer import can_id_report

router = APIRouter()

@router.get("/report/{filename}/{can_id}")
def get_report(filename: str, can_id: str):
    return can_id_report(filename, can_id)