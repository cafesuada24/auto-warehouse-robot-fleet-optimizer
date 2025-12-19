
from pydantic import PositiveInt
from pydantic.dataclasses import dataclass

from app.world.types import Coordinate


@dataclass
class Map:
    width: PositiveInt
    height: PositiveInt
    obstacles: set[Coordinate]
