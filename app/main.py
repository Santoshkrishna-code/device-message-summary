import os
from pathlib import Path
from fastapi import FastAPI, HTTPException

from app.processor import process_file

DEFAULT_DATA_FILE = Path("data/sample.jsonl")

app = FastAPI(
    title="Device Message Summary Service",
    description="Processes simulated device messages and exposes summary aggregation.",
    version="0.1.0",
)


@app.get("/summary")
def get_summary():
    """Process the configured device message input file and return the summary."""
    data_path_str = os.getenv("DATA_FILE_PATH", str(DEFAULT_DATA_FILE))
    data_path = Path(data_path_str)

    try:
        summary = process_file(data_path)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Input file not found: {data_path_str}",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read input file: {exc}",
        ) from exc

    return summary.to_dict()
