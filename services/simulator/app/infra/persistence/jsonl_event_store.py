import base64
import os
import threading
from collections.abc import Iterator
from pathlib import Path

from awrfo.logging.logger import json
from pydantic import NonNegativeInt

from .event_store import EventRecord


class JSONLEventStore:
    def __init__(
        self, filename: str = 'data/events.jsonl', *, fsync: bool = False
    ) -> None:
        self.__file = Path(filename)
        self.__file.parent.mkdir(parents=True, exist_ok=True)

        self.__fh = self.__file.open('a', encoding='utf-8', buffering=1)

        self.__lock = threading.Lock()
        self.__seq = 0

        self.__fsync = fsync

    def store(
        self,
        *,
        topic: str,
        time_ms: NonNegativeInt,
        policy: int,
        payload_type: str,
        payload_bytes: bytes,
    ) -> EventRecord:
        """Append a single event record. Returns the written record."""
        payload_b64 = base64.b64encode(payload_bytes).decode('ascii')

        with self.__lock:
            self.__seq += 1
            rec = EventRecord(
                seq=self.__seq,
                topic=topic,
                time_ms=time_ms,
                policy=policy,
                payload_type=payload_type,
                payload_b64=payload_b64,
            )
            self.__fh.write(json.dumps(rec.__dict__, separators=(',', ':')) + '\n')
            if self.__fsync:
                self.__fh.flush()
                os.fsync(self.__fh.fileno())
            return rec

    def close(self) -> None:
        with self.__lock:
            try:
                self.__fh.flush()
                if self.__fsync:
                    os.fsync(self.__fh.fileno())
            finally:
                self.__fh.close()

    @staticmethod
    def iter_file(file: str) -> Iterator[EventRecord]:
        """Iterate records from a JSONL file."""
        path = Path(file)
        with path.open('r', encoding='utf-8') as f:
            for line in f:
                ln = line.strip()
                if not ln:
                    continue
                obj = json.loads(ln)
                yield EventRecord(
                    seq=int(obj['seq']),
                    topic=str(obj['topic']),
                    time_ms=int(obj['time_ms']),
                    policy=int(obj['policy']),
                    payload_type=str(obj.get('payload_type', '')),
                    payload_b64=str(obj.get('payload_b64', '')),
                )

    @staticmethod
    def decode_payload_bytes(rec: EventRecord) -> bytes:
        return base64.b64decode(rec.payload_b64.encode("ascii"))
