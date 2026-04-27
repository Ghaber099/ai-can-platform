from fastapi import APIRouter, UploadFile, File, Form

router = APIRouter()

vehicle_profiles = {}

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    make: str = Form("Unknown"),
    model: str = Form("Unknown"),
    year: str = Form("Unknown"),
    color: str = Form("Unknown")
):
    file_location = f"uploads/{file.filename}"

    with open(file_location, "wb") as f:
        f.write(await file.read())

    vehicle_profiles[file.filename] = {
        "make": make,
        "model": model,
        "year": year,
        "color": color
    }

    return {
        "filename": file.filename,
        "vehicle": vehicle_profiles[file.filename]
    }