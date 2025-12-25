from types import MappingProxyType

from awrfo.contracts.envelopes.schema_envelope.v1.schema_envelope_pb2 import (
    SchemaEnvelope,
)
from awrfo.contracts.schemas.common.v1.coordinate_pb2 import Coordinate
from awrfo.contracts.schemas.robot.v1.robot_state_pb2 import (
    RobotState,
    RobotStateType,
)

from app.domain.models import robot
from app.domain.models.robot import RobotStateSnapshot
from app.infra.mappers.mappers import convert_to_proto

_DOMAIN_TO_PROTO_MODE = MappingProxyType(
    {
        robot.RobotState.IDLE: RobotStateType.IDLE,
        robot.RobotState.MOVING: RobotStateType.MOVING,
        robot.RobotState.WAITING: RobotStateType.WAITING,
        robot.RobotState.PICKING: RobotStateType.PICKING,
        robot.RobotState.DROPPING: RobotStateType.DROPPING,
    },
)


@convert_to_proto.register
def robot_state_snapshot_to_proto(snapshot: RobotStateSnapshot) -> RobotState:
    envelope = SchemaEnvelope(
        ts_ms=snapshot.timestamp_ms,
        producer='simulator-service',
        envelope_version=1,
    )

    return RobotState(
        envelope=envelope,
        id=str(snapshot.id),
        position=Coordinate(x=snapshot.pos[0], y=snapshot.pos[1]),
        battery=snapshot.battery,
        state=_DOMAIN_TO_PROTO_MODE.get(
            snapshot.state,
            RobotStateType.UNKNOWN,
        ),
    )
