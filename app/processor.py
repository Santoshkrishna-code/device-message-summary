import json
from pathlib import Path
from typing import Iterable

from app.models import DeviceSummary, ProcessingError, SummaryResponse

REQUIRED_KEYS = {"device_id", "sequence", "status"}


def process_lines(lines: Iterable[str]) -> SummaryResponse:
    """Process an iterable of JSON Lines strings according to specification.

    Processing order:
    1. Read line
    2. Parse JSON
    3. Validate record
    4. Check duplicate
    5. Accept record
    6. Update aggregation
    """
    accepted = 0
    duplicates = 0
    errors: list[ProcessingError] = []
    seen_pairs: set[tuple[str, int]] = set()
    device_summaries: dict[str, DeviceSummary] = {}

    for line_number, raw_line in enumerate(lines, start=1):
        # 1 & 2: Parse JSON (blank lines count as BAD_JSON)
        stripped = raw_line.strip()
        if not stripped:
            errors.append(ProcessingError(line=line_number, code="BAD_JSON"))
            continue

        try:
            data = json.loads(raw_line)
        except json.JSONDecodeError:
            errors.append(ProcessingError(line=line_number, code="BAD_JSON"))
            continue

        # 3. Validate record schema
        if not isinstance(data, dict):
            errors.append(ProcessingError(line=line_number, code="INVALID_RECORD"))
            continue

        if set(data.keys()) != REQUIRED_KEYS:
            errors.append(ProcessingError(line=line_number, code="INVALID_RECORD"))
            continue

        device_id = data["device_id"]
        if not isinstance(device_id, str) or not device_id.strip():
            errors.append(ProcessingError(line=line_number, code="INVALID_RECORD"))
            continue

        sequence = data["sequence"]
        # In Python, bool is a subclass of int (isinstance(True, int) is True).
        # We strictly check type(sequence) is int to reject booleans.
        if type(sequence) is not int or sequence < 0:
            errors.append(ProcessingError(line=line_number, code="INVALID_RECORD"))
            continue

        status = data["status"]
        if status not in ("ok", "error"):
            errors.append(ProcessingError(line=line_number, code="INVALID_RECORD"))
            continue

        # 4. Check duplicate
        pair = (device_id, sequence)
        if pair in seen_pairs:
            duplicates += 1
            continue

        # 5. Accept record
        seen_pairs.add(pair)
        accepted += 1

        # 6. Update aggregation
        if device_id not in device_summaries:
            device_summaries[device_id] = DeviceSummary(device_id=device_id)

        summary = device_summaries[device_id]
        if status == "ok":
            summary.ok += 1
        else:
            summary.error += 1

        if summary.last_sequence is None or sequence > summary.last_sequence:
            summary.last_sequence = sequence
            summary.last_status = status

    sorted_devices = sorted(device_summaries.values(), key=lambda d: d.device_id)

    return SummaryResponse(
        accepted=accepted,
        duplicates=duplicates,
        errors=errors,
        devices=sorted_devices,
    )


def process_file(file_path: str | Path) -> SummaryResponse:
    """Read a JSON Lines file from disk and return the processed SummaryResponse."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found or not a regular file: {path}")

    with path.open("r", encoding="utf-8") as f:
        return process_lines(f)
