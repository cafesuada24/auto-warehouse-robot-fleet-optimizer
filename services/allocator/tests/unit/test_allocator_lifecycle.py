import pytest
from app.application.allocator import Allocator
from awrfo.contracts.events.task.v1.task_completed_pb2 import TaskCompletedEvent

from .conftest import R1_ID, T1_ID, T2_ID
from .test_helpers import (
    get_last_command,
    make_assignment_accepted,
    make_robot_state,
    make_task_created,
)


class TestTaskLifecycle:
    def test_assignment_accepted_updates_internal_states(self, bus, drain):
        alloc = Allocator(bus=bus)

        # Setup: Create task and get assignment command
        bus.push(
            'ROBOT_STATE',
            make_robot_state(rid=str(R1_ID), x=0, y=0, ts_ms=1, battery=1.0),
        )
        bus.push(
            'TASK:CREATED',
            make_task_created(tid=str(T1_ID), px=1, py=1, deadline_ms=1000),
        )
        drain(alloc)
        drain(alloc)

        cmd = get_last_command(bus)

        # Action: Accept assignment
        bus.push(
            'TASK:ASSIGNMENT:ACCEPTED',
            make_assignment_accepted(
                task_id=str(T1_ID),
                robot_id=str(R1_ID),
                assignment_id=cmd.id,
            ),
        )
        drain(alloc)

        # Assertions using internal state checks
        assert T1_ID in getattr(alloc, '_Allocator__executing_tasks')
        assert R1_ID in getattr(alloc, '_Allocator__busy_robots')
        assert cmd.id not in getattr(alloc, '_Allocator__wait_confirm_tasks')

    def test_task_completion_frees_robot_for_next_task(self, bus, drain):
        alloc = Allocator(bus=bus)

        # Setup: Robot R1 is executing T1
        bus.push(
            'ROBOT_STATE',
            make_robot_state(rid=str(R1_ID), x=0, y=0, ts_ms=1, battery=1.0),
        )
        bus.push(
            'TASK:CREATED',
            make_task_created(tid=str(T1_ID), px=1, py=1, deadline_ms=1000),
        )
        drain(alloc)
        drain(alloc)

        cmd = get_last_command(bus)
        bus.push(
            'TASK:ASSIGNMENT:ACCEPTED',
            make_assignment_accepted(
                task_id=str(T1_ID),
                robot_id=str(R1_ID),
                assignment_id=cmd.id,
            ),
        )
        drain(alloc)

        # Action: Complete T1
        completed = TaskCompletedEvent(
            task_id=str(T1_ID), robot_id=str(R1_ID)
        ).SerializeToString()
        bus.push('TASK:COMPLETED', completed)
        drain(alloc)

        # Verify R1 can now take T2
        bus.push(
            'TASK:CREATED',
            make_task_created(tid=str(T2_ID), px=5, py=5, deadline_ms=2000),
        )
        drain(alloc)

        new_cmd = get_last_command(bus)
        assert new_cmd.assign_task.task_id == str(T2_ID)
        assert new_cmd.robot_id == str(R1_ID)
