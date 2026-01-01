# Copyright (C) 2025 Cafesuada - All Rights Reserved
#
# This source code is protected under international copyright law.  All rights
# reserved and protected by the copyright holders.
# This file is confidential and only available to authorized individuals with the
# permission of the copyright holders.  If you encounter this file and do not have
# permission, please contact the copyright holders and delete this file.

from collections.abc import Callable
from functools import singledispatch, wraps
from typing import Any, ParamSpec

P = ParamSpec('P')

_MODEL_CONVERTER_REGISTRY: dict[str, Callable[..., object]] = {}


@singledispatch
def convert_to_proto(snapshot: object) -> Any:
    raise NotImplementedError(f'No mapper registered for type: {type(snapshot)}')


def register_model_converter(
    key: str,
) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    def decorator(
        func: Callable[P, Any],
    ) -> Callable[P, Any]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> object:
            return func(*args, **kwargs)

        _MODEL_CONVERTER_REGISTRY[key] = wrapper
        return wrapper

    return decorator


def get_model_converter(key: str) -> Callable[..., Any]:
    return _MODEL_CONVERTER_REGISTRY[key]
