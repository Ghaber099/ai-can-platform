from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import analyze
from routes import upload
from routes import vehicle

app = FastAPI(title="AI CAN Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(analyze.router)
app.include_router(vehicle.router)


@app.get("/")
def home():
    return {"message": "AI CAN Platform is running"}

from services.analyzer import (
    parse_log_file,
    can_id_report,
    summary_data,
    byte_analysis_data,
    signal16_analysis_data,
    signal_data,
    scaled16_analysis_data,
)

app = FastAPI(title="AI CAN Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

vehicle_profiles = {}


def get_file_path(filename: str) -> Path:
    return UPLOAD_DIR / filename


@app.get("/")
def home():
    return {"message": "AI CAN Platform is running"}


@app.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    make: str = Form("Unknown"),
    model: str = Form("Unknown"),
    year: str = Form("Unknown"),
    color: str = Form("Unknown")
):
    file_path = get_file_path(file.filename)

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    vehicle_profiles[file.filename] = {
        "make": make or "Unknown",
        "model": model or "Unknown",
        "year": year or "Unknown",
        "color": color or "Unknown"
    }

    return {
        "message": "File uploaded successfully",
        "filename": file.filename,
        "saved_path": str(file_path),
        "vehicle": vehicle_profiles[file.filename]
    }


@app.get("/vehicle/{filename}")
def get_vehicle(filename: str):
    return vehicle_profiles.get(filename, {
        "make": "Unknown",
        "model": "Unknown",
        "year": "Unknown",
        "color": "Unknown"
    })


@app.get("/files")
def list_files():
    files = []

    for file_path in UPLOAD_DIR.iterdir():
        if file_path.is_file():
            files.append({
                "filename": file_path.name,
                "size_bytes": file_path.stat().st_size
            })

    return {
        "total_files": len(files),
        "files": files
    }


@app.get("/files/{filename}")
def read_file(filename: str):
    file_path = get_file_path(filename)

    if not file_path.exists():
        return {"error": "File not found"}

    content = file_path.read_text(errors="ignore")

    return {
        "filename": filename,
        "size_bytes": file_path.stat().st_size,
        "preview": content[:1000]
    }


@app.get("/parse/{filename}")
def parse_can_log(filename: str):
    frames = parse_log_file(filename)

    if frames is None:
        return {"error": "File not found"}

    return {
        "filename": filename,
        "total_frames": len(frames),
        "preview": frames[:20]
    }


@app.get("/can-ids/{filename}")
def get_can_ids(filename: str):
    frames = parse_log_file(filename)

    if frames is None:
        return {"error": "File not found"}

    can_ids = sorted(set(frame["can_id"] for frame in frames))

    return {
        "filename": filename,
        "total_can_ids": len(can_ids),
        "can_ids": can_ids
    }


@app.get("/summary/{filename}")
def can_id_summary(filename: str):
    return summary_data(filename)


@app.get("/byte-analysis/{filename}/{can_id}")
def byte_analysis(filename: str, can_id: str):
    return byte_analysis_data(filename, can_id)


@app.get("/signal16-analysis/{filename}/{can_id}")
def signal16_analysis(filename: str, can_id: str):
    return signal16_analysis_data(filename, can_id)


@app.get("/signal-data/{filename}/{can_id}")
def get_signal_data(filename: str, can_id: str):
    return signal_data(filename, can_id)


@app.get("/scaled16/{filename}/{can_id}")
def scaled16_analysis(filename: str, can_id: str):
    return scaled16_analysis_data(filename, can_id)


@app.get("/report/{filename}/{can_id}")
def get_report(filename: str, can_id: str):
    return can_id_report(filename, can_id)


@app.get("/report-text/{filename}/{can_id}", response_class=PlainTextResponse)
def report_text(filename: str, can_id: str):
    data = can_id_report(filename, can_id)

    if "error" in data:
        return data["error"]

    def format_text(value):
        return value.replace("_", " ").title()

    lines = [
        "==============================",
        "AI CAN ANALYSIS REPORT",
        "==============================",
        "",
        f"File: {data['filename']}",
        f"CAN ID: {data['can_id']}",
        f"Total Frames: {data['total_frames']}",
        f"Duration: {data['duration_seconds']} sec",
        f"Average Interval: {data['avg_interval_ms']} ms",
        "",
        "BYTE ANALYSIS",
        "-------------"
    ]

    for byte_info in data.get("byte_report", []):
        lines.append(
            f"Byte {byte_info['byte']}: {byte_info['role'].title()} "
            f"(min={byte_info['min']} max={byte_info['max']})"
        )

    lines.extend(["", "BIT ANALYSIS", "------------"])

    for byte_info in data.get("byte_report", []):
        byte_index = byte_info["byte"]

        if byte_info["role"] == "constant":
            lines.append(f"Byte {byte_index}: Constant byte, no useful bit activity.")
        else:
            lines.append(f"Byte {byte_index}: Changing bits detected. Likely part of numeric signal.")

    lines.extend(["", "SIGNAL ANALYSIS", "---------------"])

    for signal in data.get("signal16_report", []):
        if signal.get("role") == "constant":
            continue

        best_label = " ⭐ BEST SIGNAL" if signal.get("score", 0) >= 80 else ""

        lines.append(
            f"Signal: {signal['signal']} (Score: {signal.get('score', 0)}){best_label}"
        )
        lines.append(f"  Type: {format_text(signal.get('role', 'unknown'))}")
        lines.append(f"  Possible Meaning: {format_text(signal.get('guess', 'unknown'))}")
        lines.append(f"  Confidence: {signal.get('confidence', 0)}%")
        lines.append(
            f"  Range: {signal['scale_div_100_range'][0]} → "
            f"{signal['scale_div_100_range'][1]}"
        )

        if signal.get("anomalies"):
            lines.append(f"  ⚠ Anomalies at frames: {signal['anomalies']}")
        else:
            lines.append("  Anomalies: None detected")

        lines.append("")

    lines.extend(["SIGNAL CORRELATION", "------------------"])

    for correlation in data.get("correlations", []):
        lines.append(f"{correlation['pair']}: {correlation['correlation']}")

    lines.extend(["", "SUMMARY", "-------"])
    lines.extend(data.get("human_summary", []))

    return "\n".join(lines)
