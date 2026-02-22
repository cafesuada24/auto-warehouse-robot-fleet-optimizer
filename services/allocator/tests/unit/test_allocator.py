import math

import pytest
from app.application.allocator import Allocator

from .conftest import R1_ID, R2_ID, T1_ID
from .test_helpers import get_last_command, make_robot_state, make_task_created


class TestAllocatorProjections:
    """Tests focused on how the Allocator updates its internal state."""

    def test_robot_state_updates_latest_fields(self, bus, drain):
        alloc = Allocator(bus=bus)

        # Initial State
        bus.push(
            'ROBOT_STATE',
            make_robot_state(rid=str(R1_ID), x=1.0, y=2.0, ts_ms=10, battery=0.9),
        )
        drain(alloc)

        # Update State
        bus.push(
            'ROBOT_STATE',
            make_robot_state(rid=str(R1_ID), x=3.0, y=4.0, ts_ms=20, battery=0.5),
        )
        drain(alloc)

        # Accessing mangled private members via getattr for cleaner look (or use a test-only getter)
        robots = getattr(alloc, f'_{alloc.__class__.__name__}__robots')
        rv = robots[R1_ID]

        assert rv.pos == (3.0, 4.0)
        assert rv.ts_ms == 20
        assert math.isclose(rv.battery, 0.5)

    def test_stale_robot_update_is_dropped(self, bus, drain):
        alloc = Allocator(bus=bus)

        bus.push(
            'ROBOT_STATE',
            make_robot_state(rid=str(R1_ID), x=10.0, y=10.0, ts_ms=20, battery=0.9),
        )
        drain(alloc)
        bus.push(
            'ROBOT_STATE',
            make_robot_state(rid=str(R1_ID), x=1.0, y=2.0, ts_ms=10, battery=0.1),
        )
        drain(alloc)

        rv = getattr(alloc, f'_{alloc.__class__.__name__}__robots')[R1_ID]
        assert rv.ts_ms == 20
        assert rv.pos == (10.0, 10.0)


class TestAllocationLogic:
    """Tests focused on the assignment and bidding logic."""

    def test_assigns_to_lowest_bid_robot(self, bus, drain):
        alloc = Allocator(bus=bus)

        # R1 is at (0,0), R2 is at (10,10). Task at (1,1). R1 should win.
        bus.push(
            'ROBOT_STATE',
            make_robot_state(rid=str(R1_ID), x=0.0, y=0.0, ts_ms=1, battery=1.0),
        )
        bus.push(
            'ROBOT_STATE',
            make_robot_state(rid=str(R2_ID), x=10.0, y=10.0, ts_ms=1, battery=1.0),
        )
        bus.push(
            'TASK:CREATED',
            make_task_created(tid=str(T1_ID), px=1, py=1, deadline_ms=1000),
        )

        for _ in range(3):
            drain(alloc)

        cmd = get_last_command(bus)
        assert cmd.robot_id == str(R1_ID)
        assert cmd.assign_task.task_id == str(T1_ID)

    def test_inflight_task_not_assigned_twice(self, bus, drain):
        alloc = Allocator(bus=bus)

        bus.push(
            'ROBOT_STATE',
            make_robot_state(rid=str(R1_ID), x=0.0, y=0.0, ts_ms=1, battery=1.0),
        )
        bus.push(
            'TASK:CREATED',
            make_task_created(tid=str(T1_ID), px=1, py=1, deadline_ms=1000),
        )

        drain(alloc)
        drain(alloc)

        initial_publish_count = len(bus.published)

        # Trigger another event
        bus.push(
            'ROBOT_STATE',
            make_robot_state(rid=str(R1_ID), x=0.0, y=0.0, ts_ms=2, battery=1.0),
        )
        drain(alloc)

        assert len(bus.published) == initial_publish_count

