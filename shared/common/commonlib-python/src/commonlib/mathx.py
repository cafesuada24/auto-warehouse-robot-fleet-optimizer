from dataclasses import dataclass
import math
from typing import Iterable


def distance(u: tuple[float, float], v: tuple[float, float], *, l_n: int = 2) -> float:
    """Get distance between points.

    Args:
        u: a vector
        v: a vector that has the same length with u
        l_n: Ln Norm (L1 - Manhattan, L2 Euclidian, ...)

    Returns:
        float
    """
    if l_n < 1:
        raise ValueError("Argument 'l' must be a positive number.")

    if len(u) != len(v):
        raise ValueError(f"Vector's len mismatch: {len(u)} and {len(v)}")

    dist = 0.0
    for i in range(len(u)):
        dist += (v[i] - u[i]) ** l_n
    return dist ** (1 / l_n)


def almost_equal(a: float, b: float, *, rel: float = 1e-9, abs_: float = 1e-12) -> bool:
    """Return if two numbers are almost equal."""
    return math.isclose(a, b, rel_tol=rel, abs_tol=abs_)


def mean(xs: Iterable[float]) -> float:
    s = 0.0
    n = 0
    for x in xs:
        s += float(x)
        n += 1
    if n == 0:
        raise ValueError('mean: empty input')
    return s / n


@dataclass(frozen=True, slots=True)
class Vec2:
    """Two dimensional vector."""

    x: float
    y: float

    def norm(self) -> float:
        """Return the vector euclidian distance of the vector."""
        return math.hypot(self.x, self.y)

    def normalized(self) -> 'Vec2':
        """Normalize the vector."""
        n = self.norm()
        if n == 0.0:
            raise ValueError('Cannot normalize zero vector')
        return Vec2(self.x / n, self.y / n)

    def dot(self, other: 'Vec2') -> float:
        """Calculate the dot product with other vector."""
        return self.x * other.x + self.y * other.y

    def dist(self, other: 'Vec2') -> float:
        """Calculate distance from this to another vector."""
        return (self - other).norm()

    def __add__(self, other: 'Vec2') -> 'Vec2':
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Vec2') -> 'Vec2':
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, k: float) -> 'Vec2':
        return Vec2(self.x * k, self.y * k)

    def __rmul__(self, k: float) -> 'Vec2':
        return self.__mul__(k)
