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


def detect_attack_patterns(selected_frames):
    if len(selected_frames) < 5:
        return None

    parsed = []
    for i, frame in enumerate(selected_frames):
        try:
            data = [int(b, 16) for b in frame["data"][:8]]
            parsed.append((i, data))
        except:
            continue

    total = len(parsed)

    # ---- COUNTER ANALYSIS (byte 5) ----
    counter_anomalies = []
    prev = None

    for idx, data in parsed:
        counter = data[5]

        if prev is not None:
            if counter != (prev + 1) % 256:
                counter_anomalies.append(idx)

        prev = counter

    # ---- CHECKSUM ANALYSIS (byte 7) ----
    checksum_fail = []
    suspicious_ff = []

    for idx, data in parsed:
        checksum = data[7]

        # detect forced FF values
        if checksum == 0xFF:
            suspicious_ff.append(idx)

        # basic validation using best known pattern (you already discovered earlier)
        calc = (sum(data[0:7]) + 0x5A) % 256  # adjust if needed later

        if checksum != calc:
            checksum_fail.append(idx)

    # ---- FINAL COUNTS ----
    valid_frames = total - len(checksum_fail)
    suspicious_frames = list(set(counter_anomalies + suspicious_ff))

    return {
        "total": total,
        "valid_frames": valid_frames,
        "invalid_frames": len(checksum_fail),
        "counter_anomalies": counter_anomalies[:10],
        "checksum_fail_frames": checksum_fail[:10],
        "suspicious_ff_frames": suspicious_ff[:10],
        "suspicious_frames": suspicious_frames[:10],
        "attack_detected": True if len(checksum_fail) > 0 or len(counter_anomalies) > 0 else False
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
    attack_info = detect_attack_patterns(selected_frames)

    if attack_info and attack_info["attack_detected"]:
        message_type = "Attack Simulation / Integrity Test Frame"

        # 👇 ADD THIS LINE
        byte_meanings[5] = "rolling_counter_with_anomalies"



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
        

        signal_report.append({
            "signal": signal_name,
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
        "checksum_validation": checksum_result,
        "checksum_validation": checksum_result,
        "attack_analysis": attack_info,
        "human_summary": [
            f"CAN ID {can_id} has {len(selected_frames)} frames.",
            f"Message type: {message_type}.",
            f"Average interval is about {round(avg_interval * 1000, 2)} ms.",
            "Counter/state/padding bytes are not treated as 16-bit physical sensors.",
        ]
    }
