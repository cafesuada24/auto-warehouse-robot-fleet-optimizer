import time
from types import MappingProxyType

from app.world.models import robot
from app.world.models.robot import RobotStateSnapshot
from awrfo.contracts.envelopes.schema_envelope.v1.schema_envelope_pb2 import (
    SchemaEnvelope,
)
from awrfo.contracts.schemas.common.v1.coordinate_pb2 import Coordinate
from awrfo.contracts.schemas.robot.v1.robot_state_pb2 import (
    RobotState,
    RobotStatePayload,
    RobotStateType,
)

_DOMAIN_TO_PROTO_MODE = MappingProxyType(
    {
        robot.RobotState.IDLE: RobotStateType.IDLE,
        robot.RobotState.MOVING: RobotStateType.MOVING,
        robot.RobotState.WAITING: RobotStateType.WAITING,
        robot.RobotState.PICKING: RobotStateType.PICKING,
        robot.RobotState.DROPPING: RobotStateType.DROPPING,
    }
)


def snapshot_to_proto(
    snapshot: RobotStateSnapshot,
    time_s: float | None = None,
) -> RobotState:
    time_now_s = time.time()
    envelope = SchemaEnvelope(
        time_s=time_s or time_now_s,
        producer='simulator-service',
        envelope_version=1,
    )
    payload = RobotStatePayload(
        id=str(snapshot.robot_id),
        position=Coordinate(x=snapshot.pos[0], y=snapshot.pos[1]),
        battery=snapshot.battery,
        state=_DOMAIN_TO_PROTO_MODE.get(
            snapshot.state,
            RobotStateType.UNKNOWN,
        ),
    )

    return RobotState(
        envelope=envelope,
        payload=payload,
    )
