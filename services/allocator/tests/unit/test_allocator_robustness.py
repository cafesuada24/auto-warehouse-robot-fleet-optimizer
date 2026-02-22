import pytest
from app.application.allocator import Allocator

from .conftest import R1_ID, R2_ID, T1_ID, FakeBus
from .test_helpers import (
    get_last_command,
    make_assignment_accepted,
    make_robot_state,
    make_task_created,
)


class TestRobustness:
    def test_idempotent_assignment_accepted(self, bus, drain):
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

        payload = make_assignment_accepted(
            task_id=str(T1_ID),
            robot_id=str(R1_ID),
            assignment_id=get_last_command(bus).id,
        )

        # Push twice
        bus.push('TASK:ASSIGNMENT:ACCEPTED', payload)
        bus.push('TASK:ASSIGNMENT:ACCEPTED', payload)
        drain(alloc)
        drain(alloc)

        # Ensure only one command was ever published
        cmds = [p for t, p in bus.published if t == 'COMMAND']
        assert len(cmds) == 1

    def test_deterministic_tie_breaking(self, bus, drain):
        """Ensures that if two robots have identical bids, the winner is consistent."""

        def get_winner():
            b = FakeBus()
            a = Allocator(bus=b)
            # R1 and R2 are identical distance/battery
            b.push(
                'ROBOT_STATE',
                make_robot_state(rid=str(R1_ID), x=0, y=0, ts_ms=1, battery=1),
            )
            b.push(
                'ROBOT_STATE',
                make_robot_state(rid=str(R2_ID), x=0, y=0, ts_ms=1, battery=1),
            )
            b.push(
                'TASK:CREATED',
                make_task_created(tid=str(T1_ID), px=1, py=1, deadline_ms=1000),
            )
            for _ in range(3):
                m = b.poll()
                if m:
                    a.on_message(m.topic, m.payload)
            return get_last_command(b).robot_id

        assert get_winner() == get_winner() == str(R1_ID)
