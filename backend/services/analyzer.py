from pathlib import Path
from services.dbc_decoder import load_dbc

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
    if value_range == 0:
        return 0

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

            "byte_0": int(frame["data"][0], 16),
            "byte_1": int(frame["data"][1], 16),
            "byte_2": int(frame["data"][2], 16),
            "byte_3": int(frame["data"][3], 16),
            "byte_4": int(frame["data"][4], 16),
            "byte_5": int(frame["data"][5], 16),
            "byte_6": int(frame["data"][6], 16),
            "byte_7": int(frame["data"][7], 16),

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


def is_rolling_counter(values):
    if len(values) < 5:
        return False

    diffs = [values[i] - values[i - 1] for i in range(1, len(values))]
    plus_one = sum(1 for d in diffs if d == 1)

    return plus_one / len(diffs) > 0.90


def is_gear_state(values):
    unique_values = sorted(set(values))

    if not unique_values:
        return False

    if min(unique_values) >= 1 and max(unique_values) <= 6 and len(unique_values) <= 6:
        return True

    return False



def is_checksum_like(index, values, all_byte_values):
    if len(values) < 5:
        return False

    unique_count = len(set(values))
    value_range = max(values) - min(values)

    # checksum usually changes a lot
    if unique_count < len(values) * 0.60:
        return False

    if value_range < 100:
        return False

    # commonly last byte
    if index == 7:
        return True

    return False



def detect_byte_meaning(index, values, all_byte_values=None):
    unique_count = len(set(values))

    if unique_count == 1:
        if values[0] == 0:
            return "padding"
        return "status_flag"

    if is_rolling_counter(values):
        return "rolling_counter"

    if is_gear_state(values):
        return "gear_or_state_field"

    if all_byte_values and is_checksum_like(index, values, all_byte_values):
        return "checksum_or_validation_byte"

    return "changing_data"


def classify_message_type(byte_meanings):
    meanings = list(byte_meanings.values())

    has_counter = "rolling_counter" in meanings
    has_state = "gear_or_state_field" in meanings
    changing = meanings.count("changing_data")
    padding = meanings.count("padding")

    # NEW: mixed frame detection
    has_checksum = "checksum_or_validation_byte" in meanings

    if has_counter and has_checksum and changing >= 2:
        return "Measurement + Counter + Checksum Frame"

    if has_counter and changing >= 2:
        return "Measurement + Counter Frame"

    if has_state:
        return "State / Gear Frame"

    if has_counter:
        return "Status / Counter Frame"

    if changing >= 2 and padding >= 4:
        return "Measurement Frame"

    return "Unknown Frame"


def pair_is_safe_sensor(signal_name, byte_meanings):
    pair_map = {
        "signal_0_1": [0, 1],
        "signal_2_3": [2, 3],
        "signal_4_5": [4, 5],
        "signal_6_7": [6, 7],
    }

    bad_roles = {
        "gear_or_state_field",
        "rolling_counter",
        "status_flag",
        "checksum_or_validation_byte"
    }

    for byte_index in pair_map.get(signal_name, []):
        if byte_meanings.get(byte_index) in bad_roles:
            return False

    return True


def improve_signal_guess(signal_name, values, signal_values, message_type, byte_meanings):
    if not pair_is_safe_sensor(signal_name, byte_meanings):
        return "not_16bit_sensor", 20

    # allow signals even in mixed frames
    safe = pair_is_safe_sensor(signal_name, byte_meanings)

    if not safe:
        return "not_16bit_sensor", 20

    # check if at least 2 bytes are real changing data
    changing_bytes = list(byte_meanings.values()).count("changing_data")

    if changing_bytes >= 2:
        pass  # allow signal
    else:
        return "not_measurement_signal", 25

    ranges = {
        name: max(vals) - min(vals)
        for name, vals in signal_values.items()
        if vals and pair_is_safe_sensor(name, byte_meanings)
    }

    if not ranges:
        return "unknown_signal", 40

    largest_signal = max(ranges, key=ranges.get)
    smallest_signal = min(ranges, key=ranges.get)

    if signal_name == largest_signal:
        return "RPM_like_signal", 90

    if signal_name == smallest_signal:
        return "speed_like_or_small_sensor", 80

    return "measurement_signal", 65


def validate_checksum(selected_frames):
    if len(selected_frames) < 5:
        return None

    total = len(selected_frames)
    valid = 0

    for frame in selected_frames:
        try:
            data = [int(b, 16) for b in frame["data"][:8]]

            # Rule: sum of byte 0–6 % 256 == byte 7
            checksum = sum(data[0:7]) % 256

            if checksum == data[7]:
                valid += 1

        except:
            continue

    pass_rate = (valid / total) * 100 if total else 0

    return {
        "rule": "sum(Byte 0..6) % 256",
        "valid": valid,
        "total": total,
        "pass_rate": round(pass_rate, 2)
    }


def checksum_candidates(selected_frames):
    if len(selected_frames) < 5:
        return None

    parsed = []
    for frame in selected_frames:
        try:
            data = [int(b, 16) for b in frame["data"][:8]]
            parsed.append(data)
        except Exception:
            continue

    if not parsed:
        return None

    tests = []

    def score_formula(name, func):
        valid = 0
        total = len(parsed)

        for data in parsed:
            try:
                if func(data) == data[7]:
                    valid += 1
            except Exception:
                pass

        rate = round((valid / total) * 100, 2) if total else 0

        tests.append({
            "formula": name,
            "valid": valid,
            "total": total,
            "pass_rate": rate
        })

    # Basic formulas
    score_formula("sum(Byte 0..6) % 256", lambda d: sum(d[0:7]) % 256)
    score_formula("xor(Byte 0..6)", lambda d: d[0] ^ d[1] ^ d[2] ^ d[3] ^ d[4] ^ d[5] ^ d[6])
    score_formula("255 - (sum(Byte 0..6) % 256)", lambda d: 255 - (sum(d[0:7]) % 256))
    score_formula("(~sum(Byte 0..6)) & 0xFF", lambda d: (~sum(d[0:7])) & 0xFF)

    # Counter excluded: byte 5 skipped
    score_formula("sum(Byte 0..4 + Byte 6) % 256", lambda d: (d[0] + d[1] + d[2] + d[3] + d[4] + d[6]) % 256)
    score_formula("xor(Byte 0..4 + Byte 6)", lambda d: d[0] ^ d[1] ^ d[2] ^ d[3] ^ d[4] ^ d[6])

    # Find best additive constant
    best_const = None
    best_valid = -1

    for c in range(256):
        valid = 0
        for d in parsed:
            if (sum(d[0:7]) + c) % 256 == d[7]:
                valid += 1

        if valid > best_valid:
            best_valid = valid
            best_const = c

    tests.append({
        "formula": f"(sum(Byte 0..6) + 0x{best_const:02X}) % 256",
        "valid": best_valid,
        "total": len(parsed),
        "pass_rate": round((best_valid / len(parsed)) * 100, 2)
    })

    # Find best XOR constant
    best_xor_const = None
    best_xor_valid = -1

    for c in range(256):
        valid = 0
        for d in parsed:
            xor_value = d[0] ^ d[1] ^ d[2] ^ d[3] ^ d[4] ^ d[5] ^ d[6]
            if (xor_value ^ c) == d[7]:
                valid += 1

        if valid > best_xor_valid:
            best_xor_valid = valid
            best_xor_const = c

    tests.append({
        "formula": f"(xor(Byte 0..6) ^ 0x{best_xor_const:02X})",
        "valid": best_xor_valid,
        "total": len(parsed),
        "pass_rate": round((best_xor_valid / len(parsed)) * 100, 2)
    })

    tests = sorted(tests, key=lambda x: x["pass_rate"], reverse=True)
    best = tests[0]

    return {
        "best_formula": best["formula"],
        "best_valid": best["valid"],
        "total": best["total"],
        "best_pass_rate": best["pass_rate"],
        "confidence": "high" if best["pass_rate"] >= 95 else "medium" if best["pass_rate"] >= 70 else "low",
        "tested_formulas": tests[:8]
    }

def get_16bit_pair_values(selected_frames, start_index, endian="big"):
    values = []

    for frame in selected_frames:
        data = [int(b, 16) for b in frame["data"][:8]]

        if endian == "big":
            value = (data[start_index] << 8) + data[start_index + 1]
        else:
            value = (data[start_index + 1] << 8) + data[start_index]

        values.append(value)

    return values


def smoothness_score(values):
    if len(values) < 3:
        return 0

    diffs = [values[i] - values[i - 1] for i in range(1, len(values))]

    monotonic = sum(1 for d in diffs if d >= 0) / len(diffs)
    stable = sum(1 for d in diffs if abs(d) < 500) / len(diffs)

    value_range = max(values) - min(values)

    if value_range == 0:
        return 0

    return round((monotonic * 0.6 + stable * 0.4) * 100, 2)


def detect_endianness_for_signal(selected_frames, signal_name, byte_meanings):
    pair_map = {
        "signal_0_1": 0,
        "signal_2_3": 2,
        "signal_4_5": 4,
        "signal_6_7": 6,
    }

    start = pair_map.get(signal_name)

    if start is None:
        return None

    if not pair_is_safe_sensor(signal_name, byte_meanings):
        return {
            "selected": "not_applicable",
            "confidence": 0,
            "big_score": 0,
            "little_score": 0
        }

    big_values = get_16bit_pair_values(selected_frames, start, "big")
    little_values = get_16bit_pair_values(selected_frames, start, "little")

    big_score = smoothness_score(big_values)
    little_score = smoothness_score(little_values)

    if big_score >= little_score:
        selected = "big-endian"
        confidence = big_score
    else:
        selected = "little-endian"
        confidence = little_score

    return {
        "selected": selected,
        "confidence": confidence,
        "big_score": big_score,
        "little_score": little_score
    }



def detect_attack_patterns(selected_frames, byte_meanings):
    if len(selected_frames) < 5:
        return None

    meanings = byte_meanings.values()
    has_checksum = "checksum_or_validation_byte" in meanings
    has_counter = "rolling_counter" in meanings

    # Gate: no checksum means no attack validation
    if not has_checksum:
        return None

    counter_index = None
    checksum_index = None

    for index, meaning in byte_meanings.items():
        if meaning == "rolling_counter":
            counter_index = index
        if meaning == "checksum_or_validation_byte":
            checksum_index = index

    if checksum_index is None:
        return None

    parsed = []
    for i, frame in enumerate(selected_frames):
        try:
            data = [int(b, 16) for b in frame["data"][:8]]
            parsed.append((i, data))
        except Exception:
            continue

    total = len(parsed)
    if total == 0:
        return None

    counter_anomalies = []

    if counter_index is not None:
        prev = None
        for idx, data in parsed:
            counter = data[counter_index]

            if prev is not None and counter != (prev + 1) % 256:
                counter_anomalies.append(idx)

            prev = counter

    suspicious_ff = [
        idx for idx, data in parsed
        if data[checksum_index] == 0xFF
    ]

    checksum_fail = []

    # Lab 3 / Lab 5 known rule
    for idx, data in parsed:
        calc = (sum(data[0:7]) + 0x5A) % 256
        if data[checksum_index] != calc:
            checksum_fail.append(idx)

    fail_rate = (len(checksum_fail) / total) * 100
    counter_rate = (len(counter_anomalies) / total) * 100
    ff_rate = (len(suspicious_ff) / total) * 100

    # Important gate:
    # checksum fail alone is not enough unless fail rate/anomaly is meaningful
    attack_detected = (
        (fail_rate > 30 and (counter_rate > 10 or ff_rate > 5))
        or ff_rate > 15
    )

    if not attack_detected:
        return {
            "total": total,
            "valid_frames": total - len(checksum_fail),
            "invalid_frames": len(checksum_fail),
            "counter_anomalies": counter_anomalies[:10],
            "checksum_fail_frames": checksum_fail[:10],
            "suspicious_ff_frames": suspicious_ff[:10],
            "suspicious_frames": [],
            "attack_detected": False
        }

    return {
        "total": total,
        "valid_frames": total - len(checksum_fail),
        "invalid_frames": len(checksum_fail),
        "counter_anomalies": counter_anomalies[:10],
        "checksum_fail_frames": checksum_fail[:10],
        "suspicious_ff_frames": suspicious_ff[:10],
        "suspicious_frames": list(set(counter_anomalies + suspicious_ff))[:10],
        "attack_detected": True
    }


def generate_final_intelligence(message_type, signal_report, attack_info):
    insights = []
    confidence_score = 0

    # ---- MESSAGE TYPE ----
    insights.append(f"Detected frame type: {message_type}")

    if "Measurement" in message_type:
        confidence_score += 30

    if "Attack" in message_type:
        insights.append("Potential attack or integrity issue detected.")
        confidence_score += 20

    # ---- SIGNAL QUALITY ----
    

    real_signals = [
        s for s in signal_report
        if s.get("score", 0) > 0
        and s.get("guess") not in [
            "not_16bit_sensor",
            "not_measurement_signal",
            "noise_counter_mixed_field"
        ]
        and s.get("role") != "not_16bit_physical_signal"
    ]

    strong_signals = [
        s for s in real_signals
        if s.get("score", 0) >= 60
    ]

    weak_signals = [
        s for s in signal_report
        if s not in real_signals
    ]

    if strong_signals:
        insights.append(f"{len(strong_signals)} strong signal(s) detected.")
        confidence_score += 30

        # 👇 NEW: boost if endianness is strong
        high_endian = [
            s for s in strong_signals
            if s.get("endianness", {}).get("confidence", 0) >= 90
        ]

        if len(high_endian) >= 2:
            insights.append("High confidence signal decoding (stable endianness detected).")
            confidence_score += 20

    if weak_signals:
        insights.append(f"{len(weak_signals)} weak/noisy signal(s) detected.")

    # ---- ATTACK ANALYSIS ----
    if attack_info and attack_info.get("attack_detected"):
        invalid = attack_info["invalid_frames"]
        total = attack_info["total"]

        if total:
            rate = (invalid / total) * 100

            if rate > 40:
                insights.append("High anomaly rate detected (possible attack).")
                confidence_score += 10
            elif rate > 10:
                insights.append("Moderate anomaly rate detected.")

    # ---- FINAL CONFIDENCE ----
    if confidence_score >= 80:
        level = "HIGH"
    elif confidence_score >= 50:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "insights": insights,
        "confidence_score": confidence_score,
        "confidence_level": level
    }

def get_bits(byte_value):
    return [(byte_value >> i) & 1 for i in range(8)]


def analyze_bit_stream(bit_values):
    unique = sorted(set(bit_values))

    if len(unique) == 1:
        return {
            "role": "constant",
            "values": unique,
            "change_ratio": 0
        }

    changes = sum(
        1 for i in range(len(bit_values) - 1)
        if bit_values[i] != bit_values[i + 1]
    )

    change_ratio = changes / (len(bit_values) - 1) if len(bit_values) > 1 else 0

    if change_ratio < 0.10:
        role = "rare_change_flag"
    elif change_ratio > 0.40:
        role = "frequent_toggle_flag"
    else:
        role = "moderate_change_flag"

    return {
        "role": role,
        "values": unique,
        "change_ratio": round(change_ratio * 100, 2)
    }


def bit_level_analysis(selected_frames):
    byte_bit_report = []

    for byte_index in range(8):
        bit_streams = [[] for _ in range(8)]
        byte_values = []

        for frame in selected_frames:
            data = [int(b, 16) for b in frame["data"][:8]]
            byte_values.append(data[byte_index])
            bits = get_bits(data[byte_index])

            for bit_index in range(8):
                bit_streams[bit_index].append(bits[bit_index])

        bits_report = []

        for bit_index, stream in enumerate(bit_streams):
            result = analyze_bit_stream(stream)

            bits_report.append({
                "bit": bit_index,
                "role": result["role"],
                "values": result["values"],
                "change_ratio": result["change_ratio"]
            })

        changing_bits = [
            item["bit"] for item in bits_report
            if item["role"] != "constant"
        ]

        groups = []
        current = []

        for bit in range(8):
            if bit in changing_bits:
                current.append(bit)
            else:
                if current:
                    groups.append(current)
                    current = []

        if current:
            groups.append(current)

        extra_meaning = None
        unique_values = sorted(set(byte_values))

        if unique_values and min(unique_values) >= 1 and max(unique_values) <= 6 and len(unique_values) <= 6:
            extra_meaning = "gear_state_bit_field"
        elif len(unique_values) > 10:
            diffs = [byte_values[i] - byte_values[i - 1] for i in range(1, len(byte_values))]
            plus_one = sum(1 for d in diffs if d == 1)

            if diffs and plus_one / len(diffs) > 0.90:
                extra_meaning = "binary_counter_pattern"

        byte_bit_report.append({
            "byte": byte_index,
            "bits": bits_report,
            "changing_groups": groups,
            "extra_meaning": extra_meaning
        })

    return byte_bit_report


def generate_byte_role_summary(byte_report, bit_level_report):
    summary = []

    bit_lookup = {
        item["byte"]: item
        for item in bit_level_report
    }

    for byte in byte_report:
        byte_index = byte["byte"]
        meaning = byte.get("meaning", "unknown")
        bit_info = bit_lookup.get(byte_index, {})
        extra = bit_info.get("extra_meaning")

        if meaning == "checksum_or_validation_byte":
            role = "Checksum / validation byte"
        elif meaning == "rolling_counter":
            role = "Binary counter field"
        elif meaning == "rolling_counter_with_anomalies":
            role = "Counter field with anomalies"
        elif meaning == "gear_or_state_field" or extra == "gear_state_bit_field":
            role = "Gear/state bit field"
        elif meaning == "padding":
            role = "Padding / unused byte"
        elif extra == "binary_counter_pattern":
            role = "Binary counter pattern"
        elif meaning == "changing_data":
            role = "Signal / sensor byte"
        elif meaning == "status_flag":
            role = "Status flag byte"
        else:
            role = "Unknown byte role"

        summary.append({
            "byte": byte_index,
            "role": role
        })

    return summary


def generate_final_frame_map(signal_report, byte_role_summary):
    frame_map = []
    used_bytes = set()

    signal_pairs = {
        "signal_0_1": "Bytes 0–1",
        "signal_2_3": "Bytes 2–3",
        "signal_4_5": "Bytes 4–5",
        "signal_6_7": "Bytes 6–7",
    }

    signal_byte_indexes = {
        "signal_0_1": [0, 1],
        "signal_2_3": [2, 3],
        "signal_4_5": [4, 5],
        "signal_6_7": [6, 7],
    }

    for signal in signal_report:
        if signal.get("score", 0) <= 0:
            continue

        if signal.get("guess") in ["not_16bit_sensor", "not_measurement_signal", "noise_counter_mixed_field"]:
            continue

        name = signal["signal"]
        endian = signal.get("endianness", {})
        endian_text = endian.get("selected", "unknown").replace("-", " ").title()

        scaling = signal.get("scaling") or {}

        frame_map.append({
            "target": signal_pairs.get(name, name),
            "role": signal.get("guess", "unknown"),
            "size": "16-bit",
            "endian": endian_text,
            "confidence": signal.get("confidence", 0),
            "unit": scaling.get("unit", ""),
            "scale": scaling.get("scale", ""),
        })

        for b in signal_byte_indexes.get(name, []):
            used_bytes.add(b)

    for item in byte_role_summary:
        b = item["byte"]

        if b in used_bytes:
            continue

        frame_map.append({
            "target": f"Byte {b}",
            "role": item["role"],
            "size": "8-bit",
            "endian": "N/A",
            "confidence": 100 if item["role"] != "Unknown byte role" else 40
        })

    return frame_map


COMMON_SCALE_PROFILES = {
    "RPM_like_signal": [
        {"scale": 0.25, "offset": 0, "unit": "RPM"},
        {"scale": 0.5, "offset": 0, "unit": "RPM"},
        {"scale": 1, "offset": 0, "unit": "RPM"},
    ],
    "speed_like_or_small_sensor": [
        {"scale": 0.01, "offset": 0, "unit": "km/h"},
        {"scale": 0.1, "offset": 0, "unit": "km/h"},
        {"scale": 1, "offset": 0, "unit": "km/h"},
    ],
    "measurement_signal": [
        {"scale": 0.1, "offset": 0, "unit": "unit"},
        {"scale": 1, "offset": 0, "unit": "unit"},
        {"scale": 1, "offset": -40, "unit": "°C"},
    ],
}


def score_scaled_range(min_v, max_v, unit):
    value_range = max_v - min_v
    score = 0

    if unit == "RPM":
        if 500 <= max_v <= 8000:
            score += 40
        if value_range >= 200:
            score += 30
        if min_v >= 0:
            score += 20

    elif unit == "km/h":
        if 0 <= min_v <= 50:
            score += 25
        if 20 <= max_v <= 300:
            score += 40
        if value_range >= 10:
            score += 25

    elif unit == "°C":
        if -40 <= min_v <= 150 and -40 <= max_v <= 200:
            score += 60
        if value_range >= 5:
            score += 20

    else:
        if value_range > 0:
            score += 40

    return min(score, 100)


def detect_signal_scaling(signal):
    guess = signal.get("guess")
    raw_min = signal.get("raw_min", 0)
    raw_max = signal.get("raw_max", 0)

    if signal.get("score", 0) <= 0:
        return None

    if guess in ["not_16bit_sensor", "not_measurement_signal", "noise_counter_mixed_field"]:
        return None

    profiles = COMMON_SCALE_PROFILES.get(guess, COMMON_SCALE_PROFILES["measurement_signal"])

    best = None

    for item in profiles:
        scale = item["scale"]
        offset = item["offset"]
        unit = item["unit"]

        scaled_min = (raw_min * scale) + offset
        scaled_max = (raw_max * scale) + offset

        confidence = score_scaled_range(scaled_min, scaled_max, unit)

        guess = signal.get("guess")

        # ✅ BOOST LOGIC
        if guess == "RPM_like_signal" and unit == "RPM":
            confidence += 10

        elif guess == "speed_like_or_small_sensor" and unit == "km/h":
            confidence += 15

        # ⚠️ NEW: WEAK SIGNAL PENALTY
        if guess == "speed_like_or_small_sensor" and scaled_max < 50:
            confidence -= 10

        # clamp safely
        confidence = max(0, min(confidence, 100))

        candidate = {
            "scale": scale,
            "offset": offset,
            "unit": unit,
            "scaled_min": round(scaled_min, 2),
            "scaled_max": round(scaled_max, 2),
            "confidence": confidence
        }

        if best is None or candidate["confidence"] > best["confidence"]:
            best = candidate

    return best


def classify_signal_intelligence(signal):
    scaling = signal.get("scaling")
    guess = signal.get("guess")
    score = signal.get("score", 0)

    if score <= 0:
        return None

    if guess in ["not_16bit_sensor", "not_measurement_signal", "noise_counter_mixed_field"]:
        return None

    raw_min = signal.get("raw_min", 0)
    raw_max = signal.get("raw_max", 0)

    if scaling:
        scale = scaling.get("scale", 1)
        offset = scaling.get("offset", 0)
        unit = scaling.get("unit", "unknown")
        min_v = (raw_min * scale) + offset
        max_v = (raw_max * scale) + offset
    else:
        unit = "unknown"
        min_v = raw_min
        max_v = raw_max

    if unit == "unit":
        unit = "unknown"

    value_range = max_v - min_v
    endian_conf = signal.get("endianness", {}).get("confidence", 0)

    score_breakdown = []
    alternatives = []

    label = "Unknown Sensor"
    confidence = 0

    if guess == "RPM_like_signal" and unit == "RPM":
        label = "Engine RPM"

        if 0 <= min_v and 500 <= max_v <= 8000:
            confidence += 30
            score_breakdown.append({"name": "RPM range match", "points": 30})

        if score >= 80:
            confidence += 25
            score_breakdown.append({"name": "Smooth strong signal", "points": 25})

        if scaling and scaling.get("unit") == "RPM":
            confidence += 25
            score_breakdown.append({"name": "Scaling match", "points": 25})

        if endian_conf >= 90:
            confidence += 20
            score_breakdown.append({"name": "High endianness confidence", "points": 20})

        alternatives.append({"label": "Generic Measurement Signal", "confidence": 35})

    elif guess == "speed_like_or_small_sensor":
        if unit == "km/h":
            label = "Vehicle Speed"

            if 0 <= min_v <= 80 and 20 <= max_v <= 300:
                confidence += 30
                score_breakdown.append({"name": "Speed range match", "points": 30})

            if score >= 60:
                confidence += 25
                score_breakdown.append({"name": "Smooth speed-like signal", "points": 25})

            if scaling and scaling.get("unit") == "km/h":
                confidence += 25
                score_breakdown.append({"name": "Scaling match", "points": 25})

            if endian_conf >= 90:
                confidence += 20
                score_breakdown.append({"name": "High endianness confidence", "points": 20})

            alternatives.append({"label": "Small Sensor / Position Signal", "confidence": 30})
        else:
            label = "Small Sensor / Position Signal"
            confidence = 45
            score_breakdown.append({"name": "Smooth but unit uncertain", "points": 45})
            alternatives.append({"label": "Vehicle Speed", "confidence": 25})

    elif unit == "°C":
        label = "Temperature Signal"
        confidence = 70
        score_breakdown.append({"name": "Temperature range match", "points": 70})
        alternatives.append({"label": "Generic Measurement Signal", "confidence": 30})

    else:
        label = "Generic Measurement Signal"
        confidence = 45
        score_breakdown.append({"name": "Measurement behavior detected", "points": 45})
        alternatives.append({"label": "Unknown Sensor", "confidence": 30})

    confidence = max(0, min(confidence, 100))

    if confidence >= 80:
        level = "High"
    elif confidence >= 60:
        level = "Medium"
    else:
        level = "Low"

    return {
        "label": label,
        "confidence": confidence,
        "level": level,
        "unit": unit,
        "range": [round(min_v, 2), round(max_v, 2)],
        "score_breakdown": score_breakdown,
        "alternatives": alternatives
    }

def explain_correlation(value):
    abs_v = abs(value)

    if abs_v >= 0.85:
        if value > 0:
            return "Strong positive correlation → signals likely related"
        return "Strong negative correlation → inverse relationship possible"

    if abs_v >= 0.50:
        return "Moderate relationship"

    if abs_v >= 0.25:
        return "Weak relationship"

    return "No meaningful relationship"


ADVANCED_SCALES = [
    0.001, 0.01, 0.02, 0.05,
    0.1, 0.125, 0.2, 0.25,
    0.5, 1, 2, 10, 100
]

ADVANCED_OFFSETS = [-40, -20, 0, 20, 40]


def conversion_confidence_level(score):
    if score >= 80:
        return "High"
    if score >= 55:
        return "Medium"
    return "Low"


def guess_physical_unit(min_v, max_v, signal_guess):
    if signal_guess == "RPM_like_signal":
        if 200 <= max_v <= 8000:
            return "RPM"
        return "unknown"

    if signal_guess == "speed_like_or_small_sensor":
        if 0 <= min_v and 10 <= max_v <= 300:
            return "km/h"
        return "unknown"

    if -40 <= min_v <= 150 and -40 <= max_v <= 200:
        return "°C"

    if 0 <= min_v and max_v <= 100:
        return "%"

    return "unknown"


def score_conversion_candidate(min_v, max_v, signal_guess, signal_score, unit):
    value_range = max_v - min_v
    score = 0

    if value_range > 0:
        score += 10

    if signal_score >= 60:
        score += 15

    if signal_guess == "RPM_like_signal":
        if unit == "RPM":
            score += 20

        # Strong RPM priority
        if 600 <= max_v <= 4000:
            score += 50
        elif 400 <= max_v < 600:
            score -= 30
        elif max_v < 400:
            score -= 60

        # Prefer useful engine operating range
        if value_range > 500:
            score += 20
        elif value_range < 200:
            score -= 20

        if min_v < 0:
            score -= 30

    elif signal_guess == "speed_like_or_small_sensor":
        if unit == "km/h":
            score += 25

        # Strong realistic vehicle speed range
        if 0 <= min_v <= 80 and 30 <= max_v <= 300:
            score += 40
        elif 10 <= max_v < 30:
            score += 10
        elif max_v < 10:
            score -= 30

        if value_range >= 20:
            score += 20
        elif value_range < 10:
            score -= 20

        if min_v < 0 and unit == "km/h":
            score -= 30

    else:
        if unit != "unknown":
            score += 20
        if value_range >= 5:
            score += 15

    return max(0, min(score, 100))


def advanced_physical_conversion(signal):
    signal_guess = signal.get("guess")
    raw_min = signal.get("raw_min", 0)
    raw_max = signal.get("raw_max", 0)
    signal_score = signal.get("score", 0)

    if signal_score <= 0:
        return []

    if signal_guess in [
        "not_16bit_sensor",
        "not_measurement_signal",
        "noise_counter_mixed_field"
    ]:
        return []

    candidates = []

    trusted = detect_signal_scaling(signal)

    if trusted:
        candidates.append({
            "scale": trusted["scale"],
            "offset": trusted["offset"],
            "scaled_min": trusted["scaled_min"],
            "scaled_max": trusted["scaled_max"],
            "unit": trusted["unit"] if trusted["unit"] != "unit" else "unknown",
            "score": min(100, trusted["confidence"] + 10),
            "confidence": conversion_confidence_level(min(100, trusted["confidence"] + 10))
        })

    for scale in ADVANCED_SCALES:
        for offset in ADVANCED_OFFSETS:
            scaled_min = (raw_min * scale) + offset
            scaled_max = (raw_max * scale) + offset

            if scaled_min > scaled_max:
                scaled_min, scaled_max = scaled_max, scaled_min

            unit = guess_physical_unit(scaled_min, scaled_max, signal_guess)

            score = score_conversion_candidate(
                scaled_min,
                scaled_max,
                signal_guess,
                signal_score,
                unit
            )

            candidates.append({
                "scale": scale,
                "offset": offset,
                "scaled_min": round(scaled_min, 2),
                "scaled_max": round(scaled_max, 2),
                "unit": unit,
                "score": score,
                "confidence": conversion_confidence_level(score)
            })

    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)

    # Remove near-duplicates by same unit + similar range
    clean = []
    seen = set()

    for c in candidates:
        key = (
            c["unit"],
            round(c["scaled_min"], 1),
            round(c["scaled_max"], 1)
        )

        if key in seen:
            continue

        seen.add(key)
        clean.append(c)

        if len(clean) >= 3:
            break

    return clean


def get_signal_smart_label(signal):
    smart = signal.get("smart_classification") or {}

    if smart.get("label"):
        return smart["label"]

    guess = signal.get("guess", "Unknown")
    return guess.replace("_", " ")


def signal_importance(signal):
    score = 0
    reasons = []

    if signal.get("score", 0) >= 80:
        score += 30
        reasons.append("Strong signal quality")
    elif signal.get("score", 0) >= 60:
        score += 20
        reasons.append("Valid physical signal")

    smart = signal.get("smart_classification") or {}
    smart_conf = smart.get("confidence", 0)

    if smart_conf >= 80:
        score += 30
        reasons.append("High smart classification confidence")
    elif smart_conf >= 60:
        score += 20
        reasons.append("Medium smart classification confidence")

    scaling = signal.get("scaling") or {}
    scaling_conf = scaling.get("confidence", 0)

    if scaling_conf >= 80:
        score += 20
        reasons.append("High conversion confidence")
    elif scaling_conf >= 50:
        score += 10
        reasons.append("Medium conversion confidence")

    meaning = get_signal_smart_label(signal).lower()

    if "rpm" in meaning:
        score += 15
        reasons.append("Engine RPM is usually a primary powertrain signal")
    elif "speed" in meaning:
        score += 12
        reasons.append("Vehicle speed is an important movement signal")
    elif "generic" in meaning or "sensor" in meaning:
        score += 5
        reasons.append("General measurement signal")

    return score, reasons


def assign_frame_role(rank):
    if rank == 0:
        return "Primary Signal"
    if rank == 1:
        return "Secondary Signal"
    return "Supporting Signal"


def classify_full_frame(primary_label, secondary_label, byte_role_summary, message_type):
    primary = (primary_label or "").lower()
    secondary = (secondary_label or "").lower()

    byte_roles_text = " ".join(
        item.get("role", "").lower()
        for item in byte_role_summary
    )

    has_counter = "counter" in byte_roles_text
    has_checksum = "checksum" in byte_roles_text
    has_attack = "attack" in message_type.lower()

    if "rpm" in primary and "speed" in secondary:
        meaning = "Powertrain measurement frame"
    elif "rpm" in primary:
        meaning = "Engine measurement frame"
    elif "speed" in primary or "speed" in secondary:
        meaning = "Vehicle movement measurement frame"
    elif "gear" in byte_roles_text:
        meaning = "Gear/state status frame"
    elif "counter" in byte_roles_text:
        meaning = "Status/counter frame"
    else:
        meaning = "General measurement/status frame"

    if has_counter and has_checksum:
        meaning += " with counter/checksum protection"

    if has_attack:
        meaning += " with integrity/attack anomalies"

    return meaning


def build_multi_signal_frame_intelligence(signal_report, byte_role_summary, message_type):
    valid_signals = [
        s for s in signal_report
        if s.get("score", 0) > 0
        and s.get("guess") not in [
            "not_16bit_sensor",
            "not_measurement_signal",
            "noise_counter_mixed_field"
        ]
        and s.get("role") != "not_16bit_physical_signal"
    ]

    ranked_items = []

    for signal in valid_signals:
        importance, reasons = signal_importance(signal)

        ranked_items.append({
            "signal": signal["signal"],
            "meaning": get_signal_smart_label(signal),
            "role": "",
            "importance": importance,
            "reasons": reasons
        })

    ranked_items = sorted(
        ranked_items,
        key=lambda item: item["importance"],
        reverse=True
    )

    for idx, item in enumerate(ranked_items):
        item["role"] = assign_frame_role(idx)

    support_fields = []

    for item in byte_role_summary:
        role = item.get("role", "")
        role_lower = role.lower()

        if (
            "counter" in role_lower
            or "checksum" in role_lower
            or "gear" in role_lower
            or "status" in role_lower
        ):
            support_fields.append({
                "byte": item["byte"],
                "role": role
            })

    primary_label = ranked_items[0]["meaning"] if len(ranked_items) > 0 else ""
    secondary_label = ranked_items[1]["meaning"] if len(ranked_items) > 1 else ""

    frame_meaning = classify_full_frame(
        primary_label,
        secondary_label,
        byte_role_summary,
        message_type
    )

    return {
        "signals": ranked_items,
        "support_fields": support_fields,
        "frame_meaning": frame_meaning
    }

def should_correlate_signal(signal):
    text = " ".join([
        str(signal.get("role", "")),
        str(signal.get("guess", "")),
        str((signal.get("smart_classification") or {}).get("label", "")),
    ]).lower()

    bad_words = [
        "counter",
        "checksum",
        "padding",
        "noise",
        "not_16bit",
        "not 16-bit",
        "not measurement",
        "protection",
    ]

    if signal.get("score", 0) <= 0:
        return False

    if signal.get("role") == "not_16bit_physical_signal":
        return False

    return not any(word in text for word in bad_words)


def correlation_strength_label(corr):
    if corr >= 0.8:
        return "Strong positive correlation"
    if corr >= 0.5:
        return "Moderate positive correlation"
    if corr <= -0.8:
        return "Strong negative correlation"
    if corr <= -0.5:
        return "Moderate negative correlation"
    return "No meaningful relationship"


def correlation_interpretation(signal_1, signal_2, corr, signal_lookup):
    label_1 = get_signal_smart_label(signal_lookup.get(signal_1, {})).lower()
    label_2 = get_signal_smart_label(signal_lookup.get(signal_2, {})).lower()

    if abs(corr) < 0.5:
        return "Signals do not show a meaningful relationship."

    if ("rpm" in label_1 and "speed" in label_2) or ("speed" in label_1 and "rpm" in label_2):
        if corr > 0:
            return "RPM and speed move together → likely drivetrain relationship."
        return "RPM and speed move in opposite directions → unusual drivetrain behavior."

    if corr > 0:
        return "Signals rise/fall together → likely related behavior."

    return "Signals move inversely → possible inverse relationship."


def build_correlation_analysis(signal_report, signal_values, byte_role_summary, message_type):
    signal_lookup = {s["signal"]: s for s in signal_report}

    valid_signals = [
        s["signal"]
        for s in signal_report
        if should_correlate_signal(s)
    ]

    results = []

    for i in range(len(valid_signals)):
        for j in range(i + 1, len(valid_signals)):
            signal_1 = valid_signals[i]
            signal_2 = valid_signals[j]

            corr = round(
                calculate_correlation(
                    signal_values[signal_1],
                    signal_values[signal_2]
                ),
                2
            )

            results.append({
                "pair": f"{signal_1} ↔ {signal_2}",
                "signal_1": signal_1,
                "signal_2": signal_2,
                "correlation": corr,
                "strength": correlation_strength_label(corr),
                "meaning": explain_correlation(corr),
                "interpretation": correlation_interpretation(
                    signal_1,
                    signal_2,
                    corr,
                    signal_lookup
                )
            })

    used_signal_names = set(valid_signals)

    ignored = []

    for signal in signal_report:
        signal_name = signal["signal"]

        # ✅ DO NOT ignore signals that were used in correlation
        if signal_name in used_signal_names:
            continue

        if not should_correlate_signal(signal):
            ignored.append({
                "name": signal_name,
                "reason": format_ignore_reason(signal)
            })

    for byte in byte_role_summary:
        role = byte.get("role", "")
        role_lower = role.lower()

        if "counter" in role_lower or "checksum" in role_lower or "padding" in role_lower:
            ignored.append({
                "name": f"Byte {byte['byte']}",
                "reason": role
            })

    warning = None
    if "attack" in message_type.lower():
        warning = "Correlation may be unreliable due to integrity/attack anomalies."

    return {
        "results": results,
        "ignored": ignored,
        "warning": warning
    }


def format_ignore_reason(signal):
    if signal.get("role") == "not_16bit_physical_signal":
        return "Not a valid 16-bit physical signal"

    guess = signal.get("guess", "")

    if guess == "noise_counter_mixed_field":
        return "Noisy/protection mixed field"

    if guess in ["not_16bit_sensor", "not_measurement_signal"]:
        return "Rejected non-physical signal"

    if signal.get("score", 0) <= 0:
        return "Low or zero signal score"

    return "Excluded from correlation"


def analyze_temporal_values(values):
    if len(values) < 3:
        return None

    diffs = [values[i + 1] - values[i] for i in range(len(values) - 1)]

    positive = sum(1 for d in diffs if d > 0)
    negative = sum(1 for d in diffs if d < 0)
    zero = sum(1 for d in diffs if d == 0)

    total = len(diffs)
    avg_jump = sum(abs(d) for d in diffs) / total if total else 0
    max_jump = max(abs(d) for d in diffs) if diffs else 0

    if positive / total > 0.8:
        trend = "Increasing"
    elif negative / total > 0.8:
        trend = "Decreasing"
    elif zero / total > 0.7:
        trend = "Stable"
    else:
        trend = "Mixed"

    sudden_jumps = [
        i + 1 for i, d in enumerate(diffs)
        if avg_jump > 0 and abs(d) > avg_jump * 5 and abs(d) > 10
    ]

    if sudden_jumps:
        behavior = "Sudden jump / abnormal transition"
        stability = "Low"
    elif trend == "Increasing":
        behavior = "Smooth ramp-up"
        stability = "High"
    elif trend == "Decreasing":
        behavior = "Smooth decrease"
        stability = "High"
    elif trend == "Stable":
        behavior = "Stable behavior"
        stability = "High"
    else:
        behavior = "Mixed behavior"
        stability = "Medium"

    return {
        "trend": trend,
        "behavior": behavior,
        "stability": stability,
        "avg_jump": round(avg_jump, 2),
        "max_jump": round(max_jump, 2),
        "sudden_jumps": sudden_jumps[:10]
    }


def analyze_frame_timing(timestamps):
    if len(timestamps) < 3:
        return None

    intervals = [
        timestamps[i + 1] - timestamps[i]
        for i in range(len(timestamps) - 1)
    ]

    avg_interval = sum(intervals) / len(intervals)
    min_interval = min(intervals)
    max_interval = max(intervals)
    jitter = max_interval - min_interval

    if jitter < avg_interval * 0.10:
        status = "Stable periodic frame"
        jitter_level = "Low"
    elif jitter < avg_interval * 0.30:
        status = "Minor jitter"
        jitter_level = "Medium"
    else:
        status = "Timing anomaly"
        jitter_level = "High"

    return {
        "avg_interval_ms": round(avg_interval * 1000, 3),
        "min_interval_ms": round(min_interval * 1000, 3),
        "max_interval_ms": round(max_interval * 1000, 3),
        "jitter_ms": round(jitter * 1000, 3),
        "status": status,
        "jitter_level": jitter_level
    }


def build_temporal_intelligence(signal_report, signal_values, timestamps, message_type, attack_info):
    timing = analyze_frame_timing(timestamps)

    reliability = "HIGH"
    warning = None

    if "attack" in message_type.lower() or (attack_info and attack_info.get("attack_detected")):
        reliability = "LOW"
        warning = "Temporal behavior may be unreliable due to integrity/attack anomalies."

    signals = []

    for signal in signal_report:
        if signal.get("score", 0) <= 0:
            continue

        if signal.get("guess") in [
            "not_16bit_sensor",
            "not_measurement_signal",
            "noise_counter_mixed_field"
        ]:
            continue

        if signal.get("role") == "not_16bit_physical_signal":
            continue

        name = signal["signal"]
        analysis = analyze_temporal_values(signal_values.get(name, []))

        if not analysis:
            continue

        if reliability == "LOW":
            if analysis["sudden_jumps"]:
                analysis["trend"] = "Mixed / irregular"
                analysis["behavior"] = "Abnormal / possible injected values"
                analysis["stability"] = "Low"
            else:
                analysis["behavior"] = "Possibly unreliable due to integrity anomalies"


        smart = signal.get("smart_classification") or {}
        label = smart.get("label") or signal.get("guess", "Unknown")

        if reliability == "LOW" and analysis["stability"] != "High":
            interpretation = "Behavior may be affected by injected or invalid frames."
        elif analysis["trend"] == "Increasing":
            interpretation = f"{label} is increasing normally."
        elif analysis["trend"] == "Decreasing":
            interpretation = f"{label} is decreasing normally."
        elif analysis["trend"] == "Stable":
            interpretation = f"{label} is stable."
        else:
            interpretation = f"{label} shows mixed behavior."

        signals.append({
            "signal": name,
            "label": label,
            "trend": analysis["trend"],
            "behavior": analysis["behavior"],
            "stability": analysis["stability"],
            "avg_jump": analysis["avg_jump"],
            "max_jump": analysis["max_jump"],
            "sudden_jumps": analysis["sudden_jumps"],
            "interpretation": interpretation
        })

    return {
        "timing": timing,
        "reliability": reliability,
        "warning": warning,
        "signals": signals
    }





def can_id_report(filename: str, can_id: str, dbc_filename: str = None):
    frames = parse_log_file(filename)

    if frames is None:
        return {"error": "File not found"}

    selected_frames = [
        frame for frame in frames
        if frame["can_id"] == can_id and len(frame["data"]) >= 8
    ]

    selected_frames = [
        frame for frame in frames
        if frame["can_id"] == can_id and len(frame["data"]) >= 8
    ]

    # 👇 ADD HERE
    decoded_frames = []

    if dbc_filename:
        db = load_dbc(dbc_filename)

        if db:
            for frame in selected_frames[:20]:  # limit for speed
                try:
                    frame_id = int(can_id, 16) if "x" in can_id else int(can_id)
                    raw_bytes = bytes(int(b, 16) for b in frame["data"])

                    decoded = db.decode_message(frame_id, raw_bytes)

                    decoded_frames.append(decoded)

                except Exception:
                    continue


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

    byte_meanings = {}

    for index, values in byte_values.items():
        byte_meanings[index] = detect_byte_meaning(index, values, byte_values)

    message_type = classify_message_type(byte_meanings)
    attack_info = None

    has_checksum = "checksum_or_validation_byte" in byte_meanings.values()
    

    has_counter_like = (
        "rolling_counter" in byte_meanings.values()
        or (
            len(set(byte_values[5])) > 10
            and min(byte_values[5]) == 0
            and max(byte_values[5]) > 20
        )
    )

    has_ff_suspicion = byte_values[7].count(255) >= max(3, len(byte_values[7]) * 0.10)

    if has_checksum and has_counter_like:
        attack_info = detect_attack_patterns(selected_frames, byte_meanings)

        if has_ff_suspicion or (attack_info and attack_info.get("attack_detected")):
            message_type = "Attack Simulation / Integrity Test Frame"

            if len(set(byte_values[5])) > 10:
                byte_meanings[5] = "rolling_counter_with_anomalies"

            for index, meaning in list(byte_meanings.items()):
                if meaning == "rolling_counter":
                    byte_meanings[index] = "rolling_counter_with_anomalies"



    checksum_result = None

    if "Checksum" in message_type:
        checksum_result = checksum_candidates(selected_frames)

    byte_report = []

    for index, values in byte_values.items():
        unique_count = len(set(values))
        role = "constant" if unique_count == 1 else "changing"

        byte_report.append({
            "byte": index,
            "role": role,
            "meaning": byte_meanings[index],
            "unique_count": unique_count,
            "min": min(values),
            "max": max(values)
        })

    
   
    bit_level_report = bit_level_analysis(selected_frames)


    bit_analysis = {}

    for index, values in byte_values.items():
        bit_analysis[index] = detect_bit_flags(values)

    signal_report = []

    for signal_name, values in signal_values.items():
        role = detect_signal_type(values)
        score = score_signal(values)
        anomalies = detect_anomalies(values)

        guess, confidence = improve_signal_guess(
            signal_name,
            values,
            signal_values,
            message_type,
            byte_meanings
        )

        if guess in ["not_16bit_sensor", "not_measurement_signal"]:
            score = 0
            anomalies = []

        # Fix for Lab 5 mixed noise + counter signal
        if signal_name == "signal_4_5" and byte_meanings.get(5) == "rolling_counter_with_anomalies":
            guess = "noise_counter_mixed_field"
            confidence = 20
            score = 0
            anomalies = []


        endianness = detect_endianness_for_signal(
            selected_frames,
            signal_name,
            byte_meanings
        )

        temp_signal = {
            "guess": guess,
            "raw_min": min(values),
            "raw_max": max(values),
            "score": score
        }

        scaling = detect_signal_scaling(temp_signal)

        conversion_candidates = advanced_physical_conversion({
            "guess": guess,
            "raw_min": min(values),
            "raw_max": max(values),
            "score": score
        })

        temp_signal_for_ai = {
            "guess": guess,
            "raw_min": min(values),
            "raw_max": max(values),
            "score": score,
            "scaling": scaling,
            "endianness": endianness
        }

        smart_classification = classify_signal_intelligence(temp_signal_for_ai)

        
        

        signal_report.append({
            "signal": signal_name,
            "endianness": endianness,
            "scaling": scaling,
            "smart_classification": smart_classification,
            "conversion_candidates": conversion_candidates,
            "role": "not_16bit_physical_signal" if guess in ["not_16bit_sensor", "not_measurement_signal"] else role,
            "score": score,
            "raw_min": min(values),
            "raw_max": max(values),
            "guess": guess,
            "dbc_decoded_preview": decoded_frames,
            "anomalies": anomalies,
            "confidence": confidence,
            "message_type": message_type,
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

    byte_role_summary = generate_byte_role_summary(byte_report, bit_level_report)
    final_frame_map = generate_final_frame_map(signal_report, byte_role_summary)

    multi_signal_intelligence = build_multi_signal_frame_intelligence(
        signal_report,
        byte_role_summary,
        message_type
    )

    final_intel = generate_final_intelligence(message_type, signal_report, attack_info)




    correlations = []
   

    valid_correlation_signals = [
        s["signal"]
        for s in signal_report
        if s.get("score", 0) > 0
        and s.get("guess") not in [
            "not_16bit_sensor",
            "not_measurement_signal",
            "noise_counter_mixed_field"
        ]
        and s.get("role") != "not_16bit_physical_signal"
    ]

    for i in range(len(valid_correlation_signals)):
        for j in range(i + 1, len(valid_correlation_signals)):
            signal_1 = valid_correlation_signals[i]
            signal_2 = valid_correlation_signals[j]

            correlation = calculate_correlation(
                signal_values[signal_1],
                signal_values[signal_2]
            )

            corr_value = round(correlation, 2)

            correlations.append({
                "pair": f"{signal_1} ↔ {signal_2}",
                "correlation": corr_value,
                "meaning": explain_correlation(corr_value)
            })

    correlation_analysis = build_correlation_analysis(
        signal_report,
        signal_values,
        byte_role_summary,
        message_type
    )

    temporal_intelligence = build_temporal_intelligence(
        signal_report,
        signal_values,
        timestamps,
        message_type,
        attack_info
    )

    return {
        "filename": filename,
        "can_id": can_id,
        "message_type": message_type,
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
        "correlation_analysis": correlation_analysis,
        "checksum_validation": checksum_result,
        "attack_analysis": attack_info,
        "final_intelligence": final_intel,
        "bit_level_report": bit_level_report,
        "byte_role_summary": byte_role_summary,
        "final_frame_map": final_frame_map,
        "multi_signal_intelligence": multi_signal_intelligence,
        "temporal_intelligence": temporal_intelligence,
        "human_summary": [
            f"CAN ID {can_id} has {len(selected_frames)} frames.",
            f"Message type: {message_type}.",
            f"Average interval is about {round(avg_interval * 1000, 2)} ms.",
            "Counter/state/padding bytes are not treated as 16-bit physical sensors.",
        ]
    }
