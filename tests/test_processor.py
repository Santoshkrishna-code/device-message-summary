from pathlib import Path
import pytest

from app.models import DeviceSummary, ProcessingError
from app.processor import process_file, process_lines


def test_sample_input():
    """Test 1: Verify the required sample input from data/sample.jsonl.

    Expectations:
    - accepted = 3
    - duplicates = 1
    - errors = 1 (line 4 malformed JSON)
    - D01: ok=1, error=1, last_sequence=3, last_status="error"
    - D02: ok=0, error=1, last_sequence=2, last_status="error"
    """
    sample_path = Path("data/sample.jsonl")
    result = process_file(sample_path)

    assert result.accepted == 3
    assert result.duplicates == 1
    assert result.errors == [ProcessingError(line=4, code="BAD_JSON")]

    expected_devices = [
        DeviceSummary(
            device_id="D01",
            ok=1,
            error=1,
            last_sequence=3,
            last_status="error",
        ),
        DeviceSummary(
            device_id="D02",
            ok=0,
            error=1,
            last_sequence=2,
            last_status="error",
        ),
    ]
    assert result.devices == expected_devices


def test_out_of_order_sequence():
    """Test 2: Verify out-of-order sequence processing.

    Arrival order:
    1. D01 sequence 5 error
    2. D01 sequence 2 ok

    Latest state must be determined by highest accepted sequence (5)
    rather than arrival order (2).
    """
    lines = [
        '{"device_id":"D01","sequence":5,"status":"error"}',
        '{"device_id":"D01","sequence":2,"status":"ok"}',
    ]
    result = process_lines(lines)

    assert result.accepted == 2
    assert result.duplicates == 0
    assert result.errors == []
    assert len(result.devices) == 1

    d01 = result.devices[0]
    assert d01.device_id == "D01"
    assert d01.ok == 1
    assert d01.error == 1
    assert d01.last_sequence == 5
    assert d01.last_status == "error"


def test_empty_input():
    """Test 3: Verify empty input produces 0 counts and empty lists."""
    result = process_lines([])

    assert result.accepted == 0
    assert result.duplicates == 0
    assert result.errors == []
    assert result.devices == []


def test_malformed_json_and_blank_lines():
    """Verify malformed JSON and blank lines record BAD_JSON with 1-based line numbers."""
    lines = [
        '{"device_id":"D01","sequence":1,"status":"ok"}',
        '   ',
        '{"device_id":"D01","sequence":2,"status":',
        "",
        '{"device_id":"D01","sequence":3,"status":"ok"}',
    ]
    result = process_lines(lines)

    assert result.accepted == 2
    assert result.duplicates == 0
    assert result.errors == [
        ProcessingError(line=2, code="BAD_JSON"),
        ProcessingError(line=3, code="BAD_JSON"),
        ProcessingError(line=4, code="BAD_JSON"),
    ]
    assert len(result.devices) == 1
    assert result.devices[0].last_sequence == 3


def test_non_dict_json():
    """Verify valid JSON primitives/arrays that are not objects record INVALID_RECORD."""
    lines = [
        "123",
        '"a string"',
        "true",
        "null",
        '["item1", "item2"]',
        '{"device_id":"D01","sequence":1,"status":"ok"}',
    ]
    result = process_lines(lines)

    assert result.accepted == 1
    assert len(result.errors) == 5
    for i in range(1, 6):
        assert result.errors[i - 1] == ProcessingError(line=i, code="INVALID_RECORD")


def test_missing_and_extra_fields():
    """Verify missing fields or extra unexpected fields produce INVALID_RECORD."""
    lines = [
        '{"device_id":"D01","sequence":1}',
        '{"device_id":"D01","status":"ok"}',
        '{"sequence":1,"status":"ok"}',
        '{"device_id":"D01","sequence":1,"status":"ok","extra":"unexpected"}',
        '{"device_id":"D01","sequence":1,"status":"ok"}',
    ]
    result = process_lines(lines)

    assert result.accepted == 1
    assert len(result.errors) == 4
    for i in range(1, 5):
        assert result.errors[i - 1] == ProcessingError(line=i, code="INVALID_RECORD")


def test_invalid_device_id():
    """Verify empty string, whitespace-only, and non-string device_id are rejected."""
    lines = [
        '{"device_id":"","sequence":1,"status":"ok"}',
        '{"device_id":"   ","sequence":1,"status":"ok"}',
        '{"device_id":123,"sequence":1,"status":"ok"}',
        '{"device_id":null,"sequence":1,"status":"ok"}',
        '{"device_id":" sensor-A ","sequence":1,"status":"ok"}',
    ]
    result = process_lines(lines)

    assert result.accepted == 1
    assert len(result.errors) == 4
    assert result.devices[0].device_id == " sensor-A "


def test_sequence_validation():
    """Verify sequence rejects negatives, floats, strings, booleans, and null."""
    lines = [
        '{"device_id":"D01","sequence":-1,"status":"ok"}',
        '{"device_id":"D01","sequence":1.5,"status":"ok"}',
        '{"device_id":"D01","sequence":"1","status":"ok"}',
        '{"device_id":"D01","sequence":null,"status":"ok"}',
        '{"device_id":"D01","sequence":true,"status":"ok"}',
        '{"device_id":"D01","sequence":false,"status":"ok"}',
        '{"device_id":"D01","sequence":0,"status":"ok"}',
    ]
    result = process_lines(lines)

    assert result.accepted == 1
    assert len(result.errors) == 6
    assert result.devices[0].last_sequence == 0


def test_invalid_status():
    """Verify status must be exactly 'ok' or 'error'."""
    lines = [
        '{"device_id":"D01","sequence":1,"status":"OK"}',
        '{"device_id":"D01","sequence":2,"status":"pending"}',
        '{"device_id":"D01","sequence":3,"status":null}',
        '{"device_id":"D01","sequence":4,"status":"ok"}',
        '{"device_id":"D01","sequence":5,"status":"error"}',
    ]
    result = process_lines(lines)

    assert result.accepted == 2
    assert len(result.errors) == 3
    assert result.devices[0].ok == 1
    assert result.devices[0].error == 1


def test_duplicates_with_different_status():
    """Verify duplicate (device_id, sequence) is rejected even if status differs."""
    lines = [
        '{"device_id":"D01","sequence":1,"status":"ok"}',
        '{"device_id":"D01","sequence":1,"status":"error"}',
    ]
    result = process_lines(lines)

    assert result.accepted == 1
    assert result.duplicates == 1
    assert result.errors == []
    assert result.devices[0].ok == 1
    assert result.devices[0].error == 0
    assert result.devices[0].last_status == "ok"


def test_invalid_record_does_not_reserve_pair():
    """Validation must happen before duplicate check.

    An invalid record must not block a subsequent valid record with the same pair.
    """
    lines = [
        '{"device_id":"D01","sequence":1,"status":"invalid"}',
        '{"device_id":"D01","sequence":1,"status":"ok"}',
    ]
    result = process_lines(lines)

    assert result.accepted == 1
    assert result.duplicates == 0
    assert result.errors == [ProcessingError(line=1, code="INVALID_RECORD")]
    assert result.devices[0].ok == 1
    assert result.devices[0].last_sequence == 1


def test_device_sorting():
    """Verify devices list is sorted alphabetically by device_id."""
    lines = [
        '{"device_id":"Z99","sequence":1,"status":"ok"}',
        '{"device_id":"A01","sequence":1,"status":"ok"}',
        '{"device_id":"M50","sequence":1,"status":"ok"}',
    ]
    result = process_lines(lines)

    assert [d.device_id for d in result.devices] == ["A01", "M50", "Z99"]


def test_file_not_found():
    """Verify FileNotFoundError is raised when file does not exist."""
    with pytest.raises(FileNotFoundError):
        process_file("data/non_existent_file.jsonl")


def test_edge_cases_file():
    """Verify data/edge_cases.jsonl with edge cases."""
    result = process_file("data/edge_cases.jsonl")

    assert result.accepted == 4
    assert result.duplicates == 1
    assert len(result.errors) == 5

    assert result.errors == [
        ProcessingError(line=6, code="INVALID_RECORD"),
        ProcessingError(line=7, code="INVALID_RECORD"),
        ProcessingError(line=8, code="INVALID_RECORD"),
        ProcessingError(line=9, code="INVALID_RECORD"),
        ProcessingError(line=10, code="BAD_JSON"),
    ]

    expected_devices = [
        DeviceSummary(
            device_id="D03",
            ok=2,
            error=1,
            last_sequence=5,
            last_status="error",
        ),
        DeviceSummary(
            device_id="D04",
            ok=1,
            error=0,
            last_sequence=10,
            last_status="ok",
        ),
    ]
    assert result.devices == expected_devices


def test_larger_sample_file():
    """Verify data/larger_sample.jsonl with multi-device realistic dataset."""
    result = process_file("data/larger_sample.jsonl")

    assert result.accepted == 47
    assert result.duplicates == 5
    assert len(result.errors) == 4
    assert len(result.devices) == 10

    # Devices must be strictly sorted by device_id
    device_ids = [d.device_id for d in result.devices]
    assert device_ids == sorted(device_ids)
    assert device_ids == [f"D{i:02d}" for i in range(1, 11)]

    # Validate specific device metrics
    d01 = next(d for d in result.devices if d.device_id == "D01")
    assert d01.ok == 3
    assert d01.error == 2
    assert d01.last_sequence == 15
    assert d01.last_status == "ok"

    d02 = next(d for d in result.devices if d.device_id == "D02")
    assert d02.ok == 4
    assert d02.error == 1
    assert d02.last_sequence == 4
    assert d02.last_status == "error"
