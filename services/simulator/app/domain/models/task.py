# Copyright (C) 2025 Cafesuada - All Rights Reserved
#
# This source code is protected under international copyright law.  All rights
# reserved and protected by the copyright holders.
# This file is confidential and only available to authorized individuals with the
# permission of the copyright holders.  If you encounter this file and do not have
# permission, please contact the copyright holders and delete this file.

import dataclasses
from enum import Enum
from uuid import uuid4

from pydantic import NonNegativeInt
from pydantic.dataclasses import dataclass

from app.domain.types import Position
from app.types import IDType

from .snapshot import Snapshot


class TaskStatus(Enum):
    CREATED = 1
    ASSIGNED = 2
    EXECUTING = 3
    COMPLETED = 4
    FAILED = 5
    CANCELLED = 6

class TaskPhase(Enum):
    TO_PICKUP = 1
    PICKING = 2
    TO_DROPOFF = 3
    DROPPING = 4

@dataclasses.dataclass(frozen=True)
class TaskSnapshot(Snapshot):
    id: IDType
    pickup: Position
    dropoff: Position

    deadline_ms: NonNegativeInt

    status: TaskStatus

@dataclass
class Task:
    pickup: Position
    dropoff: Position

    deadline_ms: NonNegativeInt

    status: TaskStatus = TaskStatus.CREATED

    id: IDType = dataclasses.field(default_factory=uuid4)

    def snapshot(self, timestamp_ms: NonNegativeInt) -> TaskSnapshot:
        """Create a snapshot of the task."""
        return TaskSnapshot(
            id= self.id,
            pickup=self.pickup,
            dropoff=self.dropoff,
            status=self.status,
            deadline_ms=self.deadline_ms,
            timestamp_ms=timestamp_ms,
        )
