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
def get_report(filename: str, can_id: str, dbc: str = None):
    return can_id_report(filename, can_id, dbc)




@router.get("/report-text/{filename}/{can_id}", response_class=PlainTextResponse)
def report_text(filename: str, can_id: str):
    data = can_id_report(filename, can_id)
    message_type = data.get("message_type", "Unknown")

    if "error" in data:
        return data["error"]

    

    lines = [
        "==============================",
        "AI CAN ANALYSIS REPORT",
        "==============================",
        "",
        f"File: {data['filename']}",
        f"CAN ID: {data['can_id']}",
        f"Message Type: {message_type}",
        f"Total Frames: {data['total_frames']}",
        f"Duration: {data['duration_seconds']} sec",
        f"Average Interval: {data['avg_interval_ms']} ms",
        "",
        "BYTE ANALYSIS",
        "-------------"
    ]

    def format_text(value):
        labels = {
            "RPM_like_signal": "RPM-like signal",
            "speed_like_or_small_sensor": "Speed-like / small sensor",
            "not_16bit_sensor": "Not 16-bit sensor",
            "not_16bit_physical_signal": "Not 16-bit physical signal",
            "gear_or_state_field": "Gear/state field",
            "rolling_counter": "Rolling counter",
            "status_flag": "Status flag",
            "changing_data": "Changing data",
            "padding": "Padding",
            "smooth_increasing_signal": "Smooth increasing signal",
            "smooth_decreasing_signal": "Smooth decreasing signal",
            "not_measurement_signal": "Not measurement signal",
            "measurement_signal": "Speed-like / small sensor",
            "checksum_or_validation_byte": "Checksum / validation byte",
            "Measurement + Counter Frame": "Measurement + counter frame",
            "rolling_counter_with_anomalies": "Rolling counter with anomalies",
            "noise_counter_mixed_field": "Noise/random + counter mixed field, not physical signal",
            "rare_change_flag": "Rare-change flag",
            "frequent_toggle_flag": "Frequent toggle / active flag",
            "moderate_change_flag": "Moderate-change flag",
            "gear_state_bit_field": "Gear/state bit field",
            "binary_counter_pattern": "Binary counter pattern detected",
            "constant": "Constant / padding bit",
        }

        return labels.get(value, str(value).replace("_", " ").title())




    for byte_info in data.get("byte_report", []):
        lines.append(
            f"Byte {byte_info['byte']}: {byte_info['role'].title()} "
            f"- {format_text(byte_info.get('meaning', 'unknown'))} "
            f"(min={byte_info['min']} max={byte_info['max']})"
        )


    lines.extend(["", "MESSAGE INTERPRETATION", "----------------------"])

    if "Attack" in message_type:
        lines.append("This frame contains measurement signals plus counter/checksum integrity checks, with simulated attack failures.")
    elif "Gear" in message_type or "State" in message_type:
        lines.append("This appears to be a gear/state frame.")
    elif "Measurement + Counter + Checksum" in message_type:
        lines.append("This appears to be a measurement frame with counter and checksum protection.")
    elif "Counter" in message_type:
        lines.append("This appears to be a status/counter frame.")
    elif "Measurement" in message_type:
        lines.append("This appears to be a measurement frame with physical signals.")
    else:
        lines.append("Message role is unknown.")



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

        endian = signal.get("endianness")

        if endian and endian.get("selected") != "not_applicable" and endian.get("confidence", 0) > 0:
            selected = endian["selected"].replace("-", " ").title()
            lines.append(f"  Endianness: Selected: {selected} (confidence {endian['confidence']}%)")
            lines.append(f"  Comparison: big={endian['big_score']}%, little={endian['little_score']}%")

        lines.append(
            f"  Range: {signal['scale_div_100_range'][0]} → "
            f"{signal['scale_div_100_range'][1]}"
        )

        if signal.get("anomalies"):
            lines.append(f"  ⚠ Anomalies at frames: {signal['anomalies']}")
        else:
            lines.append("  Anomalies: None detected")

        lines.append("")

    lines.extend(["", "SIGNAL SCALING ANALYSIS", "-----------------------"])

    for signal in data.get("signal16_report", []):
        scaling = signal.get("scaling")

        if not scaling:
            continue

        lines.append(
            f"{signal['signal']} → {format_text(signal.get('guess', 'unknown'))}"
        )
        lines.append(
            f"  Raw Range: {signal.get('raw_min')} → {signal.get('raw_max')}"
        )
       

        unit = scaling.get("unit", "")

        if unit == "unit":
            unit = "unknown"

        lines.append(
            f"  Scale: ×{scaling['scale']} | Offset: {scaling['offset']}"
        )

        lines.append(
            f"  Scaled Range: {scaling['scaled_min']} → {scaling['scaled_max']} {unit}"
        )
        lines.append(
            f"  Scaling Confidence: {scaling['confidence']}%"
        )
        lines.append("")


    lines.extend(["", "SMART INTERPRETATION", "--------------------"])

    for signal in data.get("signal16_report", []):
        smart = signal.get("smart_classification")

        if not smart:
            continue

        lines.append(
            f"{signal['signal']} → {smart['label']} "
            f"({smart['level']} confidence, {smart['confidence']}%)"
        )

        lines.append(
            f"  Physical Range: {smart['range'][0]} → {smart['range'][1]} {smart['unit']}"
        )

        lines.append("  Reason:")

        for reason in smart.get("reasons", []):
            lines.append(f"  - {reason}")

        lines.append("")




    lines.extend(["", "FINAL FRAME MAP", "---------------"])

    for item in data.get("final_frame_map", []):
        lines.append(
            f"{item['target']} → {format_text(item['role'])} | "
            f"{item['size']} | {item['endian']} | confidence {item['confidence']}%"
        )



    lines.extend(["", "BYTE ROLE SUMMARY", "-----------------"])

    for item in data.get("byte_role_summary", []):
        lines.append(f"Byte {item['byte']} → {item['role']}")



    lines.extend(["", "BIT-LEVEL ANALYSIS", "------------------"])

    for byte_item in data.get("bit_level_report", []):
        lines.append(f"Byte {byte_item['byte']}:")
        if byte_item.get("extra_meaning"):
            lines.append(f"  Meaning: {format_text(byte_item['extra_meaning'])}")

        for bit in byte_item.get("bits", []):
            role = format_text(bit["role"])
            meaning_hint = ""

            if bit["role"] == "rare_change_flag":
                meaning_hint = " → possible status flag"
            elif bit["role"] == "frequent_toggle_flag":
                meaning_hint = " → active/toggling bit"
            elif bit["role"] == "constant":
                meaning_hint = " → likely padding/unused"

            lines.append(
                f"  Bit {bit['bit']}: {role}{meaning_hint} "
                f"(values={bit['values']}, change={bit['change_ratio']}%)"
            )

        if byte_item.get("changing_groups"):
            group_text = ", ".join(
                "-".join(str(b) for b in group)
                for group in byte_item["changing_groups"]
            )
            lines.append(f"  Changing bit groups: {group_text}")

        lines.append("")

    lines.extend(["SIGNAL CORRELATION", "------------------"])

    for correlation in data.get("correlations", []):
        lines.append(f"{correlation['pair']}: {correlation['correlation']}")


    checksum = data.get("checksum_validation")

    if checksum:
        lines.extend(["", "CHECKSUM ANALYSIS", "-----------------"])

        lines.append("Tested formulas:")

        for item in checksum.get("tested_formulas", []):
            marker = " ✅ BEST" if item["formula"] == checksum.get("best_formula") else ""
            lines.append(
                f"- {item['formula']} → {item['pass_rate']}% "
                f"({item['valid']} / {item['total']}){marker}"
            )

        lines.append("")
        lines.append(f"Best match: {checksum.get('best_formula')}")
        lines.append(f"Pass rate: {checksum.get('best_pass_rate')}%")
        lines.append(f"Confidence: {checksum.get('confidence')}")


    attack = data.get("attack_analysis")

    if attack and attack.get("attack_detected"):
        lines.extend(["", "ATTACK / VALIDATION ANALYSIS", "----------------------------"])

        total = attack["total"]
        valid = attack["valid_frames"]
        invalid = attack["invalid_frames"]
        checksum_fail = len(attack["checksum_fail_frames"])

        valid_rate = round((valid / total) * 100, 2) if total else 0
        invalid_rate = round((invalid / total) * 100, 2) if total else 0
        checksum_fail_rate = round((checksum_fail / total) * 100, 2) if total else 0

        lines.append(f"Total frames: {total}")
        lines.append(f"Valid frames: {valid} ({valid_rate}%)")
        lines.append(f"Invalid frames: {invalid} ({invalid_rate}%)")
        lines.append(f"Checksum fail rate: {checksum_fail_rate}%")

        lines.append("")
        lines.append(f"Counter anomalies (first 10): {attack['counter_anomalies']}")
        lines.append(f"Checksum fail frames (first 10): {attack['checksum_fail_frames']}")
        lines.append(f"Suspicious FF frames (first 10): {attack['suspicious_ff_frames']}")


    intel = data.get("final_intelligence")

    if intel:
        lines.extend(["", "FINAL INTELLIGENCE", "------------------"])

        for insight in intel.get("insights", []):
            lines.append(f"- {insight}")

        lines.append("")
        lines.append(f"Confidence Score: {intel.get('confidence_score')}")
        lines.append(f"Confidence Level: {intel.get('confidence_level')}")


    
    lines.extend(["", "SUMMARY", "-------"])
    lines.extend(data.get("human_summary", []))

    return "\n".join(lines)