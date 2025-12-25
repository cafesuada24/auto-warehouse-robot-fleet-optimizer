from functools import singledispatch
from typing import Any


@singledispatch
def convert_to_proto(snapshot: object) -> Any:
    raise NotImplementedError(f'No mapper registered for type: {type(snapshot)}')
