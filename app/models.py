from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ProcessingError:
    line: int
    code: str


@dataclass
class DeviceSummary:
    device_id: str
    ok: int = 0
    error: int = 0
    last_sequence: int | None = None
    last_status: str | None = None


@dataclass
class SummaryResponse:
    accepted: int
    duplicates: int
    errors: list[ProcessingError]
    devices: list[DeviceSummary]

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "duplicates": self.duplicates,
            "errors": [asdict(err) for err in self.errors],
            "devices": [asdict(dev) for dev in self.devices],
        }
