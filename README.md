# Device Message Summary Service

A small Python service that processes simulated device messages from a JSON Lines (`.jsonl`) file and exposes the resulting summary through a lightweight HTTP API.

## Tech Stack

- **Python 3.11+**
- **FastAPI** — lightweight HTTP API framework
- **Uvicorn** — ASGI production/development server
- **pytest** — automated test suite
- **HTTPX / FastAPI TestClient** — HTTP API integration testing
- **JSON Lines** — line-delimited JSON input format
- Python standard library for file handling, JSON parsing, dataclasses, and typing

*No database, message queues, Docker, or external frontend dependencies.*

## Project Structure

```text
device-message-summary/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── processor.py
│   └── models.py
├── data/
│   └── sample.jsonl
├── tests/
│   ├── test_processor.py
│   └── test_api.py
├── README.md
├── requirements.txt
├── pyproject.toml
└── .gitignore
```

- `app/models.py` — internal dataclasses (`ProcessingError`, `DeviceSummary`, `SummaryResponse`)
- `app/processor.py` — JSONL parsing, validation, deduplication, and aggregation logic
- `app/main.py` — FastAPI application and `GET /summary` endpoint
- `data/sample.jsonl` — sample JSON Lines input file
- `tests/` — automated unit and API integration tests

## Prerequisites

- Python 3.11 or newer
- pip
- Git

## Setup

Clone the repository and navigate into the project directory:

```bash
git clone https://github.com/Santoshkrishna-code/device-message-summary.git
cd device-message-summary
```

Create and activate a virtual environment:

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

## Input Format

The application reads a JSON Lines (`.jsonl`) file where each line is expected to be a JSON object with exactly three keys:

```json
{
  "device_id": "D01",
  "sequence": 1,
  "status": "ok"
}
```

### Validation Rules

- `device_id`:
  - Must be a string
  - Non-empty and not whitespace-only
  - Valid values are preserved exactly as supplied (e.g., `" sensor-A "` is preserved with whitespace intact)
- `sequence`:
  - Must be an integer $\ge 0$
  - Boolean values (`true`, `false`) are explicitly rejected
- `status`:
  - Must be exactly `"ok"` or `"error"`
- The JSON object must contain exactly `device_id`, `sequence`, and `status` (no missing keys, no unexpected extra keys).

## Processing Rules

Each line is processed independently following this strict order:

```text
read line → parse JSON → validate record → check duplicate → accept record → update aggregation
```

1. **Malformed JSON:** Any syntax error in JSON produces a `BAD_JSON` error with its 1-based line number.
2. **Blank Lines:** Empty or whitespace-only lines are treated as `BAD_JSON`.
3. **Record Validation:** Valid JSON that fails schema validation produces an `INVALID_RECORD` error with its 1-based line number. Validation occurs **before** duplicate detection, ensuring an invalid record never reserves a `(device_id, sequence)` pair.
4. **Duplicate Detection:** For valid records, uniqueness is defined by the pair `(device_id, sequence)`. Only the first valid occurrence is accepted. Subsequent valid occurrences increment the duplicate count, even if their status differs.
5. **Aggregation:**
   - Accepted records increment the device's `ok` or `error` count.
   - The device's `last_sequence` and `last_status` are determined strictly by the highest accepted `sequence` number, not by file arrival order.
6. **Device Ordering:** Devices are returned in a list sorted alphabetically by `device_id`.
7. **Empty Input:** An empty input file returns zero counts and empty lists (`errors: []`, `devices: []`) without error.

## Running the API

Start the development server with Uvicorn:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### API Usage

Fetch the processed summary:

```bash
curl http://127.0.0.1:8000/summary
```

Expected response for the sample input:

```json
{
  "accepted": 3,
  "duplicates": 1,
  "errors": [
    {
      "line": 4,
      "code": "BAD_JSON"
    }
  ],
  "devices": [
    {
      "device_id": "D01",
      "ok": 1,
      "error": 1,
      "last_sequence": 3,
      "last_status": "error"
    },
    {
      "device_id": "D02",
      "ok": 0,
      "error": 1,
      "last_sequence": 2,
      "last_status": "error"
    }
  ]
}
```

If the input file cannot be read or is missing, the endpoint returns an HTTP 500 error instead of a misleading empty result:

```json
{
  "detail": "Input file not found: data/sample.jsonl"
}
```

## Running Tests

Execute the automated test suite with pytest:

```bash
pytest
```

To run with verbose output:

```bash
pytest -v
```

The test suite covers:
- The required sample file with expected counts, errors, and device summaries.
- Out-of-order sequence processing verifying that latest status tracks the highest sequence number.
- Empty input handling.
- Edge cases: malformed JSON lines, blank lines, non-object JSON, missing and extra fields, invalid device IDs, boolean/float/negative sequences, invalid statuses, duplicate records with different statuses, and invalid records preceding valid records.
- API tests verifying HTTP 200 response structure and HTTP 500 file-read failure handling.

## Design Choice

The core processing logic in `app/processor.py` is kept completely decoupled from the FastAPI web framework in `app/main.py`.

The processor operates directly on standard Python iterables of strings (`process_lines`) and file paths (`process_file`), returning clean, typed dataclass structures (`app/models.py`). This allows:
- Direct, fast, in-memory unit testing without spinning up HTTP servers.
- Clear separation of concerns: the HTTP layer handles request routing, environment configuration, and status code mapping, while the processor focuses solely on data validation, deduplication, and aggregation logic.

## Assumptions

- The input file is a local UTF-8 JSON Lines file.
- The input dataset is suitable for in-memory processing.
- Error reporting only requires the 1-based line number and standard error code (`BAD_JSON` or `INVALID_RECORD`).
- For any `(device_id, sequence)` pair, the first valid occurrence is authoritative; duplicates are ignored for device state calculations.
- Device summaries include only accepted, non-duplicate records.

## Known Limitation

The input file is read and processed when `/summary` is requested rather than being continuously monitored or streamed. This is sufficient for the assignment's small local-file scope.

## Time Spent

Actual time spent: TBD

## Unfinished Work

No required functionality has been left unfinished. The processor, API endpoints, error handling, sample dataset, and automated tests are fully implemented and verified.

## AI and Reuse Note

- AI tools were used for requirement analysis, implementation discussion, edge-case review, and documentation assistance.
- The code was reviewed, refined, and tested for this assignment.
- No private employer material, credentials, secrets, or private chat histories were used.

## React Integration

- A React page can call `GET /summary` using `fetch` or a data-fetching library (such as TanStack Query) and maintain an active `loading` state while the request is in-flight.
- A non-2xx HTTP status code or network exception triggers an `error` state, displaying a clear failure alert (e.g., when the input file cannot be read).
- A 200 OK response with an empty `devices` list renders a dedicated `empty` state informing the user that no records were present.
- A 200 OK response with data populates the dashboard displaying summary metrics (`accepted`, `duplicates`, `errors`) and the sorted device table.
- Keeping `loading`, `empty`, `error`, and `success` states distinct prevents confusing an empty dataset with an API outage.

## Walkthrough

### 1. Project Structure
The repository is organized into distinct modules:
- `app/models.py`: Strongly typed dataclasses for records, errors, and responses.
- `app/processor.py`: Pure business logic for parsing, validating, deduplicating, and aggregating.
- `app/main.py`: FastAPI server exposing `GET /summary`.
- `data/sample.jsonl`: 5-line sample file with duplicates and a malformed record.
- `tests/`: 16 comprehensive unit and integration tests.

### 2. Starting the Server
Start Uvicorn from the project root:
```bash
uvicorn app.main:app --port 8000
```

### 3. Calling `/summary`
Run `curl` against the summary endpoint:
```bash
curl http://127.0.0.1:8000/summary
```

### 4. Sample Output
The API returns HTTP 200 with the exact expected aggregation:
```json
{
  "accepted": 3,
  "duplicates": 1,
  "errors": [
    {
      "line": 4,
      "code": "BAD_JSON"
    }
  ],
  "devices": [
    {
      "device_id": "D01",
      "ok": 1,
      "error": 1,
      "last_sequence": 3,
      "last_status": "error"
    },
    {
      "device_id": "D02",
      "ok": 0,
      "error": 1,
      "last_sequence": 2,
      "last_status": "error"
    }
  ]
}
```

### 5. Failure Case
If the input file is missing or unreadable, the API returns HTTP 500:
```bash
DATA_FILE_PATH=data/non_existent.jsonl curl -i http://127.0.0.1:8000/summary
# HTTP/1.1 500 Internal Server Error
# {"detail":"Input file not found: data/non_existent.jsonl"}
```

### 6. Running Tests
Run all 16 tests via pytest:
```bash
pytest -v
# ======================== 16 passed in 0.46s =========================
```

### 7. Design Choice
Decoupling the JSON Lines stream processor from FastAPI allows verifying edge cases (such as duplicate keys, blank lines, out-of-order sequence updates, and type constraints) purely in memory without spinning up network sockets.

### 8. Defect Found and Fixed
**Defect:** In Python, `bool` is a subclass of `int` (`isinstance(True, int) == True`). When validating `"sequence"`, using a standard `isinstance(sequence, int)` check inadvertently allowed boolean values `true` and `false` to be accepted as integer sequences `1` and `0`.
**Fix:** Explicitly enforced `type(sequence) is int and sequence >= 0` in `app/processor.py` to reject boolean values and correctly flag them as `INVALID_RECORD`.
