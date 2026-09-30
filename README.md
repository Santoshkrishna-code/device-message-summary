# Device Message Summary Service

A small Python service that processes simulated device messages from a JSON Lines (`.jsonl`) file and exposes the resulting summary through a lightweight HTTP API.

## Tech Stack

- **Python 3.11+**
- **FastAPI** — HTTP API
- **Uvicorn** — ASGI server
- **pytest** — automated testing
- **HTTPX / FastAPI TestClient** — API testing
- **JSON Lines** — input format
- No database or external services

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

## Prerequisites

- Python 3.11 or newer
- pip
- Git

## Setup

Clone the repository and enter the project directory:

```bash
git clone <REPOSITORY_URL>
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

Install dependencies:

```bash
pip install -r requirements.txt
```

## Input Format

The application reads a JSON Lines file where each non-empty line is expected to contain exactly:

```json
{
  "device_id": "D01",
  "sequence": 1,
  "status": "ok"
}
```

### Validation rules

- `device_id` must be a non-empty string and cannot contain only whitespace.
- The supplied `device_id` value is preserved as-is.
- `sequence` must be an integer greater than or equal to `0`.
- Boolean values are not accepted as sequences.
- `status` must be either `"ok"` or `"error"`.
- A record must contain exactly `device_id`, `sequence`, and `status`.

## Processing Rules

Each input line is processed independently.

1. Malformed JSON produces a `BAD_JSON` error with its 1-based line number.
2. Blank lines are treated as `BAD_JSON`.
3. Valid JSON that does not satisfy the record schema produces an `INVALID_RECORD` error.
4. Validation happens before duplicate detection.
5. The first valid occurrence of a `(device_id, sequence)` pair is accepted.
6. Later occurrences of the same pair are counted as duplicates, even if their status differs.
7. The latest device status is determined by the highest accepted sequence, not by input order.
8. Devices are returned sorted by `device_id`.
9. Processing continues after malformed or invalid records.

## Sample Input

`data/sample.jsonl` contains:

```json
{"device_id":"D01","sequence":1,"status":"ok"}
{"device_id":"D01","sequence":1,"status":"ok"}
{"device_id":"D02","sequence":2,"status":"error"}
{"device_id":"D01","sequence":3,"status":"error"}
```

The sample also contains one intentionally malformed JSON line.

Expected totals:

```text
accepted:   3
duplicates: 1
errors:     1
```

Expected device summaries:

```text
D01:
  ok: 1
  error: 1
  last_sequence: 3
  last_status: error

D02:
  ok: 0
  error: 1
  last_sequence: 2
  last_status: error
```

## Running the API

Start the development server:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

### Get the summary

```bash
curl http://127.0.0.1:8000/summary
```

The endpoint returns the processed summary as JSON.

If the input file cannot be read, the API returns an appropriate HTTP error instead of incorrectly returning an empty successful result.

## Running Tests

Run the complete test suite:

```bash
pytest
```

The automated tests cover:

1. The supplied sample and its expected totals/device summaries.
2. A lower sequence arriving after a higher sequence, verifying that the latest status is based on sequence rather than input order.
3. Empty input, verifying zero totals and empty error/device lists.

Additional edge cases may be covered where useful.

## Design Choice

The message processing logic is kept separate from the FastAPI route.

The processor is responsible for parsing, validation, duplicate detection, and aggregation, while the API layer is responsible only for exposing the resulting summary and handling file-read failures.

This keeps the core behavior independently testable and prevents HTTP concerns from being mixed with the processing logic.

## Known Limitation

The input file is read and processed when `/summary` is requested rather than being continuously streamed or monitored for changes. This is intentional because the assignment requires a small solution with no database or background processing.

## Assumptions

- The configured input file is a local JSONL file.
- The file is small enough to process in memory.
- Error entries only need their error code and 1-based line number.
- The first valid occurrence of a `(device_id, sequence)` pair always wins.
- A duplicate does not affect per-device counts or latest-sequence information.
- Device summaries contain only accepted records.

## React Integration

- A React page can call `GET /summary` using `fetch` or a data-fetching library and keep a loading state while the request is pending.
- A successful response with no devices can render a dedicated empty state instead of treating it as an API error.
- A non-2xx response or network failure can be captured and displayed as an API failure state.
- A successful response containing devices can render the totals and per-device summaries.
- The UI should keep loading, empty, and error states separate so users can distinguish a valid empty result from a failed request.

## AI and Reuse Note

AI tools were used as development assistance for understanding the requirements, discussing implementation approaches, reviewing edge cases, and checking documentation structure.

The resulting implementation was written and reviewed for this assignment rather than copied as an existing solution. The final behavior was verified using the automated test suite and manual API checks.

No private employer material, credentials, secrets, or private chat history were used.

## Time Spent

**Target:** approximately 2 hours, in line with the suggested effort cap.

Actual time spent will be recorded here after completing the implementation.

## Unfinished Work

No unfinished functionality is intentionally left in the required scope.

Any additional improvements considered but not implemented will be documented here after the effort cap is reached.

## Walkthrough

A short walkthrough accompanies this submission.

It demonstrates:

1. The project structure and processing flow.
2. Starting the API.
3. Calling `GET /summary`.
4. The resulting summary for the sample data.
5. A failure case where the input file cannot be read.
6. The automated tests running successfully.
7. One design choice.
8. One defect found during development and how it was fixed.

---
