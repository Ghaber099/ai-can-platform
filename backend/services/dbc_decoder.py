from pathlib import Path
import cantools

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DBC_DIR = BASE_DIR / "dbc_files"
DBC_DIR.mkdir(exist_ok=True)


def get_dbc_path(filename: str) -> Path:
    return DBC_DIR / filename


def save_dbc_file(upload_file):
    file_path = get_dbc_path(upload_file.filename)

    with file_path.open("wb") as buffer:
        buffer.write(upload_file.file.read())

    return file_path


def load_dbc(filename: str):
    file_path = get_dbc_path(filename)

    if not file_path.exists():
        return None

    try:
        return cantools.database.load_file(str(file_path), database_format="dbc")
    except Exception as error:
        print("DBC load error:", error)
        return None


def list_dbc_files():
    return [
        file.name
        for file in DBC_DIR.iterdir()
        if file.is_file() and (
            file.suffix.lower() == ".dbc" or file.name.lower().endswith(".dbc.txt")
        )
    ]


def decode_frame_with_dbc(dbc_filename: str, can_id: str, data_bytes: list):
    db = load_dbc(dbc_filename)

    if db is None:
        return {"error": "DBC file not found"}

    try:
        frame_id = int(can_id, 16)
    except ValueError:
        frame_id = int(can_id)

    raw_bytes = bytes(int(byte, 16) for byte in data_bytes)

    try:
        decoded = db.decode_message(frame_id, raw_bytes)
        return {
            "can_id": can_id,
            "decoded": decoded
        }
    except Exception as error:
        return {
            "can_id": can_id,
            "error": str(error)
        }