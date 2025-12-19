from pydantic import NonNegativeFloat, NonNegativeInt

type Position = tuple[NonNegativeFloat, NonNegativeFloat]
type Coordinate = tuple[NonNegativeInt, NonNegativeInt]
