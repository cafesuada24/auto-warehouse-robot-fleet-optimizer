# Copyright (C) 2025 Cafesuada - All Rights Reserved
#
# This source code is protected under international copyright law.  All rights
# reserved and protected by the copyright holders.
# This file is confidential and only available to authorized individuals with the
# permission of the copyright holders.  If you encounter this file and do not have
# permission, please contact the copyright holders and delete this file.

from functools import singledispatch
from typing import Any


@singledispatch
def convert_to_proto(snapshot: object) -> Any:
    raise NotImplementedError(f'No mapper registered for type: {type(snapshot)}')
