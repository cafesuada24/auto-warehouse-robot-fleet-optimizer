import dataclasses
import random
from uuid import uuid4

from pydantic import NonNegativeInt, PositiveInt
from pydantic.dataclasses import dataclass

from app.domain.models.snapshot import Snapshot
from app.domain.types import Coordinate
from app.types import IDType


@dataclasses.dataclass(frozen=True)
class MapSnapshot(Snapshot):
    width: PositiveInt
    height: PositiveInt
    obstacles: set[Coordinate]


@dataclass
class Map:
    width: PositiveInt
    height: PositiveInt
    obstacles: set[Coordinate]

    id: IDType = dataclasses.field(default_factory=uuid4)

    @staticmethod
    def random(
        size: tuple[PositiveInt, PositiveInt],
        seed: PositiveInt = 1234,
        num_obstacles: PositiveInt | float = 0.3,
    ) -> 'Map':
        """Random a map with a given size.

        Args:
            size: map size
            seed: random seed
            num_obstacles: either an interger or a float number. An integer
                represents number of obstacle and cannot be larger than the
                number of cells in the map. Otherwise, it represent the percentage
                of obstacles.

        Returns:
            A generated map.
        """
        if (
            isinstance(num_obstacles, int)
            and num_obstacles > size[0] * size[1]
            or isinstance(num_obstacles, float)
            and (num_obstacles <= 0 or num_obstacles > 1.0)
        ):
            raise ValueError('Number of obstacles are exceed the map size.')

        obstacles: set[Coordinate] = set()

        random.seed(seed)

        if isinstance(num_obstacles, int):
            while num_obstacles > 0:
                ob = (random.randint(0, size[0] - 1), random.randint(0, size[1] - 1))
                if ob in obstacles:
                    continue
                obstacles.add(ob)
                num_obstacles -= 1
        else:
            for i in range(size[0]):
                for j in range(size[1]):
                    if random.random() <= num_obstacles:
                        obstacles.add((i, j))

        return Map(
            width=size[0],
            height=size[1],
            obstacles=obstacles,
        )

    def snapshot(self, timestamp_ms: NonNegativeInt) -> MapSnapshot:
        return MapSnapshot(
            id=self.id,
            timestamp_ms=timestamp_ms,
            width=self.width,
            height=self.height,
            obstacles=self.obstacles,
        )
