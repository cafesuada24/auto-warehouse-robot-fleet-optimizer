from awrfo.contracts.commands.v1.action_command_pb2 import ActionCommand
from awrfo.contracts.events.task.v1.task_assigned_pb2 import TaskAssignedEvent
from awrfo.contracts.events.task.v1.task_assignment_rejected_pb2 import (
    RejectionReason,
    TaskAssignmentRejectedEvent,
)
from awrfo.contracts.events.task.v1.task_created_pb2 import TaskCreatedEvent
from awrfo.contracts.schemas.robot.v1.robot_state_pb2 import RobotState


def make_robot_state(
    *,
    rid: str,
    x: float,
    y: float,
    ts_ms: int,
    battery: float,
) -> bytes:
    msg = RobotState(id=rid, ts_ms=ts_ms, battery=battery)
    msg.position.x, msg.position.y = x, y
    return msg.SerializeToString()


def make_task_created(
    *,
    tid: str,
    px: int,
    py: int,
    deadline_ms: int,
    ts_ms: int = 0,
) -> bytes:
    msg = TaskCreatedEvent(task_id=tid, deadline_ms=deadline_ms, ts_ms=ts_ms)
    msg.pickup.x, msg.pickup.y = px, py
    return msg.SerializeToString()


def make_assignment_accepted(
    *,
    task_id: str,
    robot_id: str,
    assignment_id: str,
    ts_ms: int = 0,
) -> bytes:
    return TaskAssignedEvent(
        task_id=task_id,
        robot_id=robot_id,
        assignment_id=assignment_id,
        ts_ms=ts_ms,  # if exists; remove if not
    ).SerializePartialToString()


def make_assignment_rejected(
    *,
    task_id: str,
    robot_id: str,
    assignment_id: str,
    reason: RejectionReason,
    ts_ms: int = 0,
) -> bytes:
    return TaskAssignmentRejectedEvent(
        task_id=task_id,
        robot_id=robot_id,
        assignment_id=assignment_id,
        ts_ms=ts_ms,  # if exists; remove if not
        reason=reason,
    ).SerializePartialToString()


def get_last_command(bus) -> ActionCommand:
    topic, payload = bus.published[-1]
    return ActionCommand.FromString(payload)
