from typing import Protocol

from app.domain.models.robot import RobotStateSnapshot
from app.domain.models.task import TaskSnapshot


class EventPublisher(Protocol):
    def publish_task_completed_event(self, snapshot: TaskSnapshot) -> None:
        ...

    def publish_task_created_event(self, snapshot: TaskSnapshot) -> None:
        ...

    def publish_robot_state(self, snapshot: RobotStateSnapshot) -> None:
        ...
