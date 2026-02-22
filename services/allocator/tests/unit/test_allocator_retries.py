import pytest
from app.application.allocator import Allocator
from awrfo.contracts.events.task.v1.task_assignment_rejected_pb2 import RejectionReason

from .conftest import R1_ID, T1_ID
from .test_helpers import (
    get_last_command,
    make_assignment_rejected,
    make_robot_state,
    make_task_created,
)


class TestRetryLogic:
    FUTURE_TS = 999_999_999  # Constant for 'time has passed'

    def test_rejected_task_moves_to_wait_retry(self, bus, drain):
        alloc = Allocator(bus=bus)
        bus.push(
            'ROBOT_STATE',
            make_robot_state(rid=str(R1_ID), x=0, y=0, ts_ms=1, battery=1),
        )
        bus.push(
            'TASK:CREATED',
            make_task_created(tid=str(T1_ID), px=1, py=1, deadline_ms=1000),
        )
        drain(alloc)
        drain(alloc)

        cmd = get_last_command(bus)
        bus.push(
            'TASK:ASSIGNMENT:REJECTED',
            make_assignment_rejected(
                task_id=str(T1_ID),
                robot_id=str(R1_ID),
                assignment_id=cmd.id,
                reason=RejectionReason.REJECTION_REASON_TEMPORARY_BUSY,
            ),
        )
        drain(alloc)

        assert T1_ID in getattr(alloc, '_Allocator__wait_retry_tasks')
        assert R1_ID not in getattr(alloc, '_Allocator__busy_robots')

    def test_task_dropped_after_max_retries(self, bus, drain):
        alloc = Allocator(bus=bus, max_retry_count=1)

        bus.push(
            'ROBOT_STATE',
            make_robot_state(rid=str(R1_ID), x=0, y=0, ts_ms=1, battery=1),
        )
        bus.push(
            'TASK:CREATED',
            make_task_created(tid=str(T1_ID), px=1, py=1, deadline_ms=1000),
        )
        drain(alloc)
        drain(alloc)

        # First Rejection
        cmd = get_last_command(bus)
        bus.push(
            'TASK:ASSIGNMENT:REJECTED',
            make_assignment_rejected(
                task_id=str(T1_ID),
                robot_id=str(R1_ID),
                assignment_id=cmd.id,
                reason=RejectionReason.REJECTION_REASON_TEMPORARY_BUSY,
            ),
        )
        drain(alloc)

        # Trigger retry
        alloc._Allocator__flush_retrying_tasks(now=self.FUTURE_TS)
        alloc._Allocator__try_allocate()

        # Second Rejection
        cmd2 = get_last_command(bus)
        bus.push(
            'TASK:ASSIGNMENT:REJECTED',
            make_assignment_rejected(
                task_id=str(T1_ID),
                robot_id=str(R1_ID),
                assignment_id=cmd2.id,
                reason=RejectionReason.REJECTION_REASON_TEMPORARY_BUSY,
            ),
        )
        drain(alloc)

        # After exceeding max_retry_count (1), task should be purged
        assert T1_ID not in getattr(alloc, '_Allocator__tasks')
