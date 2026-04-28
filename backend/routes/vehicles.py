from fastapi import APIRouter
from database import get_connection
from datetime import datetime

router = APIRouter()


@router.post("/vehicle/save")
def save_vehicle(data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO vehicles
    (vin, plate, make, model, year, color, ecu, engine, owner_license, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("vin"),
        data.get("plate"),
        data.get("make"),
        data.get("model"),
        data.get("year"),
        data.get("color"),
        data.get("ecu"),
        data.get("engine"),
        data.get("ownerLicense"),
        data.get("notes"),
        datetime.now().isoformat()
    ))

    vehicle_id = cursor.lastrowid
    owner_license = data.get("ownerLicense")

    if owner_license:
        cursor.execute("""
        SELECT id FROM customer_vehicles
        WHERE customer_license = ? AND vehicle_id = ?
        """, (owner_license, vehicle_id))

        existing = cursor.fetchone()

        if not existing:
            cursor.execute("""
            INSERT INTO customer_vehicles
            (customer_license, vehicle_id, relationship_type, created_at)
            VALUES (?, ?, ?, ?)
            """, (
                owner_license,
                vehicle_id,
                "owner",
                datetime.now().isoformat()
            ))

    conn.commit()
    conn.close()

    return {
        "status": "saved",
        "vehicle_id": vehicle_id
    }


@router.get("/vehicles/search")
def search_vehicles(q: str = ""):
    conn = get_connection()
    cursor = conn.cursor()

    search = f"%{q}%"

    cursor.execute("""
    SELECT id, vin, plate, make, model, year, color, ecu, engine, owner_license, notes, created_at
    FROM vehicles
    WHERE vin LIKE ?
       OR plate LIKE ?
       OR make LIKE ?
       OR model LIKE ?
       OR year LIKE ?
       OR owner_license LIKE ?
    ORDER BY id DESC
    """, (search, search, search, search, search, search))

    rows = cursor.fetchall()
    conn.close()

    return {
        "total": len(rows),
        "vehicles": [
            {
                "id": row[0],
                "vin": row[1],
                "plate": row[2],
                "make": row[3],
                "model": row[4],
                "year": row[5],
                "color": row[6],
                "ecu": row[7],
                "engine": row[8],
                "ownerLicense": row[9],
                "notes": row[10],
                "createdAt": row[11],
            }
            for row in rows
        ]
    }


@router.get("/vehicles/customer/{license}")
def vehicles_by_customer(license: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT v.id, v.vin, v.plate, v.make, v.model, v.year, v.color, v.ecu, v.engine, v.notes, v.created_at
    FROM vehicles v
    JOIN customer_vehicles cv ON cv.vehicle_id = v.id
    WHERE cv.customer_license = ?
    ORDER BY v.id DESC
    """, (license,))

    rows = cursor.fetchall()
    conn.close()

    return {
        "total": len(rows),
        "vehicles": [
            {
                "id": row[0],
                "vin": row[1],
                "plate": row[2],
                "make": row[3],
                "model": row[4],
                "year": row[5],
                "color": row[6],
                "ecu": row[7],
                "engine": row[8],
                "notes": row[9],
                "createdAt": row[10],
            }
            for row in rows
        ]
    }


@router.post("/customer-vehicle/link")
def link_customer_vehicle(data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    customer_license = data.get("customer_license")
    vehicle_id = data.get("vehicle_id")
    relationship_type = data.get("relationship_type", "owner")

    cursor.execute("""
    SELECT id FROM customer_vehicles
    WHERE customer_license = ? AND vehicle_id = ?
    """, (customer_license, vehicle_id))

    existing = cursor.fetchone()

    if not existing:
        cursor.execute("""
        INSERT INTO customer_vehicles
        (customer_license, vehicle_id, relationship_type, created_at)
        VALUES (?, ?, ?, ?)
        """, (
            customer_license,
            vehicle_id,
            relationship_type,
            datetime.now().isoformat()
        ))

    conn.commit()
    conn.close()

    return {"status": "linked"}