from pydantic.dataclasses import dataclass

from app.types import IDType

from .map import Map
from .robot import Robot
from .task import Task


@dataclass
class World:
    map: Map
    robots: dict[IDType, Robot] = {}
    tasks: dict[IDType, Task] = {}
    time: float = 0.0
