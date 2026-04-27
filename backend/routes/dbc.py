from fastapi import APIRouter, UploadFile, File

from services.dbc_decoder import (
    save_dbc_file,
    list_dbc_files,
    decode_frame_with_dbc,
)

router = APIRouter()


@router.post("/dbc/upload")
def upload_dbc(file: UploadFile = File(...)):
    file_path = save_dbc_file(file)

    return {
        "message": "DBC uploaded successfully",
        "filename": file.filename,
        "saved_path": str(file_path)
    }


@router.get("/dbc/list")
def list_dbcs():
    files = list_dbc_files()

    return {
        "total_dbc_files": len(files),
        "dbc_files": files
    }


@router.get("/dbc/decode/{dbc_filename}/{can_id}")
def decode_one_frame(dbc_filename: str, can_id: str, data: str):
    """
    Example:
    /dbc/decode/test.dbc/100?data=04 01 00 03 00 00 00 00
    """

    data_bytes = data.split()

    return decode_frame_with_dbc(dbc_filename, can_id, data_bytes)