from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from services.analyzer import (
    parse_log_file,
    can_id_report,
    signal_data,
)

router = APIRouter()


@router.get("/can-ids/{filename}")
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


@router.get("/signal-data/{filename}/{can_id}")
def get_signal_data(filename: str, can_id: str):
    return signal_data(filename, can_id)


@router.get("/report/{filename}/{can_id}")
def get_report(filename: str, can_id: str):
    return can_id_report(filename, can_id)


@router.get("/report-text/{filename}/{can_id}", response_class=PlainTextResponse)
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