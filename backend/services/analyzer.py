from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


def get_file_path(filename: str) -> Path:
    return UPLOAD_DIR / filename


def parse_log_file(filename: str):
    file_path = get_file_path(filename)

    if not file_path.exists():
        return None

    frames = []

    with file_path.open("r", errors="ignore") as file:
        for line_number, line in enumerate(file, start=1):
            parts = line.strip().split()

            if len(parts) < 4:
                continue

            try:
                timestamp = float(parts[0])
                can_id = parts[1]
                dlc = int(parts[2])
                data = parts[3:3 + dlc]
            except ValueError:
                continue

            if len(data) != dlc:
                continue

            frames.append({
                "line": line_number,
                "timestamp": timestamp,
                "can_id": can_id,
                "dlc": dlc,
                "data": data
            })

    return frames


def get_16bit_signals(data):
    byte_values = [int(b, 16) for b in data[:8]]

    return {
        "signal_0_1": (byte_values[0] << 8) + byte_values[1],
        "signal_2_3": (byte_values[2] << 8) + byte_values[3],
        "signal_4_5": (byte_values[4] << 8) + byte_values[5],
        "signal_6_7": (byte_values[6] << 8) + byte_values[7],
    }


def detect_signal_type(values):
    if len(values) < 2:
        return "unknown"

    diffs = [values[i] - values[i - 1] for i in range(1, len(values))]

    increasing = sum(1 for d in diffs if d >= 0)
    decreasing = sum(1 for d in diffs if d <= 0)

    increasing_ratio = increasing / len(diffs)
    decreasing_ratio = decreasing / len(diffs)

    value_range = max(values) - min(values)
    avg_diff = sum(abs(d) for d in diffs) / len(diffs)

    if value_range == 0:
        return "constant"

    if increasing_ratio > 0.9 and avg_diff < 200:
        return "smooth_increasing_signal"

    if decreasing_ratio > 0.9 and avg_diff < 200:
        return "smooth_decreasing_signal"

    if avg_diff > 300:
        return "noisy_signal"

    if value_range > 100:
        return "dynamic_signal"

    return "unknown"


def guess_signal_name(values):
    if len(values) < 2:
        return "unknown", 0

    raw_max = max(values)
    value_range = raw_max - min(values)
    unique_count = len(set(values))
    scaled_100_max = raw_max / 100

    diffs = [values[i] - values[i - 1] for i in range(1, len(values))]
    avg_diff = sum(abs(d) for d in diffs) / len(diffs)

    increasing = sum(1 for d in diffs if d >= 0)
    increasing_ratio = increasing / len(diffs)

    if (
        increasing_ratio > 0.9 and
        value_range > 500 and
        avg_diff < 150 and
        10 <= scaled_100_max <= 200 and
        unique_count > 20
    ):
        return "LIKELY_VEHICLE_SPEED", 85

    if scaled_100_max <= 5:
        return "small_sensor_or_angle", 60

    if value_range > 2000:
        return "large_dynamic_sensor", 55

    return "unknown_signal", 40


def detect_bit_flags(values):
    bit_results = []

    for bit in range(8):
        bit_values = [(value >> bit) & 1 for value in values]
        unique_values = sorted(set(bit_values))

        role = "constant" if len(unique_values) == 1 else "toggle_flag"

        bit_results.append({
            "bit": bit,
            "role": role,
            "values": unique_values
        })

    return bit_results


def detect_rpm(values):
    if len(values) < 5:
        return False

    diffs = [values[i] - values[i - 1] for i in range(1, len(values))]

    positive = sum(1 for d in diffs if d > 0)
    negative = sum(1 for d in diffs if d < 0)

    ratio_pos = positive / len(diffs)
    ratio_neg = negative / len(diffs)

    value_range = max(values) - min(values)

    return (
        0.3 < ratio_pos < 0.7 and
        0.3 < ratio_neg < 0.7 and
        value_range > 100
    )


def calculate_correlation(values1, values2):
    if len(values1) != len(values2) or len(values1) < 2:
        return 0

    mean1 = sum(values1) / len(values1)
    mean2 = sum(values2) / len(values2)

    numerator = sum((x - mean1) * (y - mean2) for x, y in zip(values1, values2))
    denom1 = sum((x - mean1) ** 2 for x in values1)
    denom2 = sum((y - mean2) ** 2 for y in values2)

    if denom1 == 0 or denom2 == 0:
        return 0

    return numerator / (denom1 ** 0.5 * denom2 ** 0.5)


def score_signal(values):
    if len(values) < 2:
        return 0

    value_range = max(values) - min(values)

    diffs = [values[i] - values[i - 1] for i in range(1, len(values))]
    avg_diff = sum(abs(d) for d in diffs) / len(diffs)

    increasing = sum(1 for d in diffs if d >= 0)
    increasing_ratio = increasing / len(diffs)

    score = 0

    if increasing_ratio > 0.9:
        score += 30

    if value_range > 300:
        score += 30

    if avg_diff < 150:
        score += 20

    if avg_diff < 300:
        score += 10

    return score


def detect_anomalies(values):
    anomalies = []

    if len(values) < 3:
        return anomalies

    diffs = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    avg_diff = sum(diffs) / len(diffs)

    if avg_diff == 0:
        return anomalies

    for i in range(1, len(values)):
        if abs(values[i] - values[i - 1]) > avg_diff * 3:
            anomalies.append(i)

    return anomalies


def summary_data(filename: str):
    frames = parse_log_file(filename)

    if frames is None:
        return {"error": "File not found"}

    summary = {}

    for frame in frames:
        can_id = frame["can_id"]
        timestamp = frame["timestamp"]

        if can_id not in summary:
            summary[can_id] = {
                "can_id": can_id,
                "total_frames": 0,
                "dlc": frame["dlc"],
                "first_timestamp": timestamp,
                "last_timestamp": timestamp,
                "timestamps": []
            }

        summary[can_id]["total_frames"] += 1
        summary[can_id]["last_timestamp"] = timestamp
        summary[can_id]["timestamps"].append(timestamp)

    results = []

    for can_id, data in summary.items():
        timestamps = data["timestamps"]
        intervals = [
            timestamps[i] - timestamps[i - 1]
            for i in range(1, len(timestamps))
        ]

        avg_interval = sum(intervals) / len(intervals) if intervals else 0

        results.append({
            "can_id": can_id,
            "total_frames": data["total_frames"],
            "dlc": data["dlc"],
            "first_timestamp": data["first_timestamp"],
            "last_timestamp": data["last_timestamp"],
            "avg_interval_seconds": avg_interval,
            "avg_interval_ms": round(avg_interval * 1000, 3)
        })

    return {
        "filename": filename,
        "total_can_ids": len(results),
        "summary": results
    }


def byte_analysis_data(filename: str, can_id: str):
    frames = parse_log_file(filename)

    if frames is None:
        return {"error": "File not found"}

    byte_values = {}

    for frame in frames:
        if frame["can_id"] != can_id:
            continue

        for index, byte_hex in enumerate(frame["data"]):
            try:
                byte_values.setdefault(index, []).append(int(byte_hex, 16))
            except ValueError:
                continue

    results = []

    for index, values in byte_values.items():
        unique_values = sorted(set(values))

        results.append({
            "byte_index": index,
            "total_values": len(values),
            "unique_count": len(unique_values),
            "min": min(values),
            "max": max(values),
            "first_10_values": values[:10],
            "is_constant": len(unique_values) == 1
        })

    return {
        "filename": filename,
        "can_id": can_id,
        "byte_analysis": results
    }


def signal16_analysis_data(filename: str, can_id: str):
    frames = parse_log_file(filename)

    if frames is None:
        return {"error": "File not found"}

    signals = {
        "signal_0_1": [],
        "signal_2_3": [],
        "signal_4_5": [],
        "signal_6_7": []
    }

    for frame in frames:
        if frame["can_id"] != can_id:
            continue

        if len(frame["data"]) < 8:
            continue

        signal_values = get_16bit_signals(frame["data"])

        for name, value in signal_values.items():
            signals[name].append(value)

    results = []

    for name, values in signals.items():
        if not values:
            continue

        results.append({
            "signal": name,
            "total_values": len(values),
            "unique_count": len(set(values)),
            "min": min(values),
            "max": max(values),
            "first_10_values": values[:10],
            "last_10_values": values[-10:],
            "is_constant": len(set(values)) == 1
        })

    return {
        "filename": filename,
        "can_id": can_id,
        "signal16_analysis": results
    }


def signal_data(filename: str, can_id: str):
    frames = parse_log_file(filename)

    if frames is None:
        return {"error": "File not found"}

    signal_frames = []

    for frame in frames:
        if frame["can_id"] != can_id:
            continue

        if len(frame["data"]) < 8:
            continue

        signals = get_16bit_signals(frame["data"])

        signal_frames.append({
            "timestamp": frame["timestamp"],
            "frame_index": len(signal_frames),
            "can_id": frame["can_id"],
            "dlc": frame["dlc"],
            "data": frame["data"],
            "signal_0_1": signals["signal_0_1"],
            "signal_2_3": signals["signal_2_3"],
            "signal_4_5": signals["signal_4_5"],
            "signal_6_7": signals["signal_6_7"]
        })

    return {
        "filename": filename,
        "can_id": can_id,
        "total_frames": len(signal_frames),
        "frames": signal_frames
    }


def scaled16_analysis_data(filename: str, can_id: str):
    signal_data_result = signal_data(filename, can_id)

    if "error" in signal_data_result:
        return signal_data_result

    raw_signals = {
        "signal_0_1": [],
        "signal_2_3": [],
        "signal_4_5": [],
        "signal_6_7": []
    }

    for frame in signal_data_result["frames"]:
        for signal_name in raw_signals:
            raw_signals[signal_name].append(frame[signal_name])

    results = {}

    for signal_name, values in raw_signals.items():
        if not values:
            continue

        results[signal_name] = {
            "raw_min": min(values),
            "raw_max": max(values),
            "raw_first_10": values[:10],
            "scale_div_10_first_10": [round(v / 10, 2) for v in values[:10]],
            "scale_div_100_first_10": [round(v / 100, 2) for v in values[:10]],
            "scale_div_1000_first_10": [round(v / 1000, 3) for v in values[:10]],
            "scale_div_10_min_max": [round(min(values) / 10, 2), round(max(values) / 10, 2)],
            "scale_div_100_min_max": [round(min(values) / 100, 2), round(max(values) / 100, 2)],
            "scale_div_1000_min_max": [round(min(values) / 1000, 3), round(max(values) / 1000, 3)]
        }

    return {
        "filename": filename,
        "can_id": can_id,
        "scaled16": results
    }


def can_id_report(filename: str, can_id: str):
    frames = parse_log_file(filename)

    if frames is None:
        return {"error": "File not found"}

    selected_frames = [
        frame for frame in frames
        if frame["can_id"] == can_id and len(frame["data"]) >= 8
    ]

    if not selected_frames:
        return {"error": "No frames found for this CAN ID"}

    timestamps = [frame["timestamp"] for frame in selected_frames]
    intervals = [
        timestamps[i] - timestamps[i - 1]
        for i in range(1, len(timestamps))
    ]

    avg_interval = sum(intervals) / len(intervals) if intervals else 0

    byte_values = {index: [] for index in range(8)}
    signal_values = {
        "signal_0_1": [],
        "signal_2_3": [],
        "signal_4_5": [],
        "signal_6_7": []
    }

    for frame in selected_frames:
        data = [int(byte_hex, 16) for byte_hex in frame["data"][:8]]

        for index in range(8):
            byte_values[index].append(data[index])

        signals = get_16bit_signals(frame["data"])

        for signal_name, value in signals.items():
            signal_values[signal_name].append(value)

    byte_report = []

    for index, values in byte_values.items():
        unique_count = len(set(values))
        role = "constant" if unique_count == 1 else "changing"

        byte_report.append({
            "byte": index,
            "role": role,
            "unique_count": unique_count,
            "min": min(values),
            "max": max(values)
        })

    bit_analysis = {}

    for index, values in byte_values.items():
        bit_analysis[index] = detect_bit_flags(values)

    signal_report = []

    for signal_name, values in signal_values.items():
        role = detect_signal_type(values)
        score = score_signal(values)
        anomalies = detect_anomalies(values)
        guess, confidence = guess_signal_name(values)

        if detect_rpm(values):
            guess = "RPM_SIGNAL_DETECTED"
            confidence = 85

        signal_report.append({
            "signal": signal_name,
            "role": role,
            "score": score,
            "raw_min": min(values),
            "raw_max": max(values),
            "guess": guess,
            "anomalies": anomalies,
            "confidence": confidence,
            "scale_div_10_range": [
                round(min(values) / 10, 2),
                round(max(values) / 10, 2)
            ],
            "scale_div_100_range": [
                round(min(values) / 100, 2),
                round(max(values) / 100, 2)
            ],
            "first_10_raw": values[:10]
        })

    signal_report = sorted(signal_report, key=lambda item: item["score"], reverse=True)

    correlations = []
    signals_list = list(signal_values.keys())

    for i in range(len(signals_list)):
        for j in range(i + 1, len(signals_list)):
            signal_1 = signals_list[i]
            signal_2 = signals_list[j]

            correlation = calculate_correlation(
                signal_values[signal_1],
                signal_values[signal_2]
            )

            correlations.append({
                "pair": f"{signal_1} ↔ {signal_2}",
                "correlation": round(correlation, 2)
            })

    return {
        "filename": filename,
        "can_id": can_id,
        "total_frames": len(selected_frames),
        "first_timestamp": timestamps[0],
        "last_timestamp": timestamps[-1],
        "duration_seconds": round(timestamps[-1] - timestamps[0], 4),
        "avg_interval_seconds": round(avg_interval, 6),
        "avg_interval_ms": round(avg_interval * 1000, 3),
        "byte_report": byte_report,
        "bit_analysis": bit_analysis,
        "signal16_report": signal_report,
        "correlations": correlations,
        "human_summary": [
            f"CAN ID {can_id} has {len(selected_frames)} frames.",
            f"Average interval is about {round(avg_interval * 1000, 2)} ms.",
            "Bytes with constant values are probably not useful signals.",
            "16-bit pairs marked likely_signal may contain speed, RPM, throttle, angle, or sensor values."
        ]
    }
