import sqlite3

DB_NAME = "ai_can.db"

def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Customers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        license TEXT PRIMARY KEY,
        name TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        notes TEXT,
        created_at TEXT
    )
    """)

    # Vehicles
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vin TEXT,
        plate TEXT,
        make TEXT,
        model TEXT,
        year TEXT,
        color TEXT,
        ecu TEXT,
        engine TEXT,
        owner_license TEXT,
        notes TEXT,
        created_at TEXT
    )
    """)

    # Repairs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS repairs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER,
        date TEXT,
        mileage TEXT,
        title TEXT,
        work_done TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS owners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER,
        name TEXT,
        license TEXT,
        phone TEXT,
        created_at TEXT
    )
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customer_vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_license TEXT,
        vehicle_id INTEGER,
        relationship_type TEXT,
        created_at TEXT
    )
    """)



    conn.commit()
    conn.close()


    # Owners history
    