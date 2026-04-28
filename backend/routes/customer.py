from fastapi import APIRouter
from database import get_connection
from datetime import datetime

router = APIRouter()

@router.post("/customer/save")
def save_customer(data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO customers
    (license, name, phone, email, address, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["license"],
        data.get("name"),
        data.get("phone"),
        data.get("email"),
        data.get("address"),
        data.get("notes"),
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

    return {"status": "saved"}


@router.get("/customer/{license}")
def get_customer(license: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM customers WHERE license=?", (license,))
    row = cursor.fetchone()

    conn.close()

    if not row:
        return {"error": "not found"}

    return {
        "license": row[0],
        "name": row[1],
        "phone": row[2],
        "email": row[3],
        "address": row[4],
        "notes": row[5]
    }

@router.get("/customers/search")
def search_customers(q: str = ""):
    conn = get_connection()
    cursor = conn.cursor()

    search = f"%{q}%"

    cursor.execute("""
    SELECT license, name, phone, email, address, notes
    FROM customers
    WHERE license LIKE ?
       OR name LIKE ?
       OR phone LIKE ?
    """, (search, search, search))

    rows = cursor.fetchall()
    conn.close()

    return {
        "total": len(rows),
        "customers": [
            {
                "license": row[0],
                "name": row[1],
                "phone": row[2],
                "email": row[3],
                "address": row[4],
                "notes": row[5]
            }
            for row in rows
        ]
    }

@router.get("/customer/{license}/timeline")
def customer_timeline(license: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT cv.created_at, cv.relationship_type, v.id, v.make, v.model, v.year, v.vin, v.plate
    FROM customer_vehicles cv
    JOIN vehicles v ON v.id = cv.vehicle_id
    WHERE cv.customer_license = ?
    ORDER BY cv.id DESC
    """, (license,))
    vehicle_links = cursor.fetchall()

    cursor.execute("""
    SELECT r.date, r.mileage, r.title, r.work_done, v.id, v.make, v.model, v.vin, v.plate
    FROM repairs r
    JOIN vehicles v ON v.id = r.vehicle_id
    JOIN customer_vehicles cv ON cv.vehicle_id = v.id
    WHERE cv.customer_license = ?
    ORDER BY r.id DESC
    """, (license,))
    repairs = cursor.fetchall()

    conn.close()

    return {
        "vehicle_links": [
            {
                "date": row[0],
                "relationship": row[1],
                "vehicle_id": row[2],
                "make": row[3],
                "model": row[4],
                "year": row[5],
                "vin": row[6],
                "plate": row[7],
            }
            for row in vehicle_links
        ],
        "repairs": [
            {
                "date": row[0],
                "mileage": row[1],
                "title": row[2],
                "work_done": row[3],
                "vehicle_id": row[4],
                "make": row[5],
                "model": row[6],
                "vin": row[7],
                "plate": row[8],
            }
            for row in repairs
        ]
    }

@router.get("/customers/vehicle/{vehicle_id}")
def customers_by_vehicle(vehicle_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT c.license, c.name, c.phone, c.email, c.address, c.notes, cv.created_at
    FROM customers c
    JOIN customer_vehicles cv ON cv.customer_license = c.license
    WHERE cv.vehicle_id = ?
    ORDER BY cv.id DESC
    """, (vehicle_id,))

    rows = cursor.fetchall()
    conn.close()

    return {
        "total": len(rows),
        "customers": [
            {
                "license": row[0],
                "name": row[1],
                "phone": row[2],
                "email": row[3],
                "address": row[4],
                "notes": row[5],
                "created_at": row[6],
            }
            for row in rows
        ]
    }