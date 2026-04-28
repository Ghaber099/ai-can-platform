from fastapi import APIRouter
from database import get_connection
from datetime import datetime

router = APIRouter()


@router.post("/owner/save")
def save_owner(data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO owners
    (vehicle_id, name, license, phone, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (
        data.get("vehicle_id"),
        data.get("name"),
        data.get("license"),
        data.get("phone"),
        datetime.now().isoformat()
    ))

    conn.commit()
    owner_id = cursor.lastrowid
    conn.close()

    return {
        "status": "saved",
        "owner_id": owner_id
    }


@router.get("/owners/vehicle/{vehicle_id}")
def get_owners_by_vehicle(vehicle_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, vehicle_id, name, license, phone, created_at
    FROM owners
    WHERE vehicle_id = ?
    ORDER BY id DESC
    """, (vehicle_id,))

    rows = cursor.fetchall()
    conn.close()

    return {
        "total": len(rows),
        "owners": [
            {
                "id": row[0],
                "vehicle_id": row[1],
                "name": row[2],
                "license": row[3],
                "phone": row[4],
                "created_at": row[5],
            }
            for row in rows
        ]
    }