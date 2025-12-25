from dataclasses import dataclass

from pydantic.types import NonNegativeInt


@dataclass(frozen=True)
class Snapshot:
    timestamp_ms: NonNegativeInt
