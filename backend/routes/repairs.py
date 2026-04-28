from fastapi import APIRouter
from database import get_connection

router = APIRouter()


@router.post("/repair/save")
def save_repair(data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO repairs
    (vehicle_id, date, mileage, title, work_done)
    VALUES (?, ?, ?, ?, ?)
    """, (
        data.get("vehicle_id"),
        data.get("date"),
        data.get("mileage"),
        data.get("title"),
        data.get("work_done"),
    ))

    conn.commit()
    repair_id = cursor.lastrowid
    conn.close()

    return {
        "status": "saved",
        "repair_id": repair_id
    }


@router.get("/repairs/vehicle/{vehicle_id}")
def get_repairs_by_vehicle(vehicle_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, vehicle_id, date, mileage, title, work_done
    FROM repairs
    WHERE vehicle_id = ?
    ORDER BY id DESC
    """, (vehicle_id,))

    rows = cursor.fetchall()
    conn.close()

    return {
        "total": len(rows),
        "repairs": [
            {
                "id": row[0],
                "vehicle_id": row[1],
                "date": row[2],
                "mileage": row[3],
                "title": row[4],
                "work_done": row[5],
            }
            for row in rows
        ]
    }