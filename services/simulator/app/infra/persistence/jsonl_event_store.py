import base64
from collections.abc import Generator
from dataclasses import asdict

from awrfo.logging.logger import json

from app.application.events.domain_event import DomainEvent
from app.infra.mappers.mappers import convert_to_proto


def _domain_event_to_dict(data: DomainEvent) -> dict[str, int | float | str]:
    proto_type = convert_to_proto(data.payload)
    serialized: bytes = proto_type.SerializeToString()
    itemdict = asdict(data)
    itemdict['payload_type'] = data.payload.__class__.__name__
    itemdict['payload'] = base64.b64encode(serialized).decode('ascii')
    itemdict['policy'] = data.policy.value
    return itemdict

class JSONLEventStore:
    def __init__(self, filename: str = 'data/events.jsonl') -> None:
        self.__filename = filename

    def store(self, event: DomainEvent) -> None:
        data = _domain_event_to_dict(event)
        with open(self.__filename, 'a') as f:
            json.dump(data, f)
            f.write('\n')

    def iter(self) -> Generator[DomainEvent]:
        ...
        # with open(self.__filename) as f:
        #     line = f.readline()
        #     if not line:
        #         return
        #     itemdict = json.loads(line)
        #     yield DomainEvent(
        #         topic=itemdict['topic'],
        #         time_ms=itemdict['time_ms'],
        #         policy=QoSPolicy(itemdict['policy']),
        #         payload=base64.b64decode(itemdict['payload'].encode('ascii')),
        #     )


