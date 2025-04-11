from .line import ILine
from .world_point import IWorldPoint, WorldPoint
from .plane import IPlane
import numpy as np


def intersection(plane: IPlane, line: ILine) -> IWorldPoint:
    """
    Calculate intersection between a line and a Plane.
    :param plane: Plane to intersect
    :param line: Line to intersect
    :return: 3D intersection point
    """
    p: float = plane.r - np.dot(plane.c.point, line.p)
    q: np.ndarray = np.dot(plane.c.point, line.a.T)
    intersect = line.p + p / q * line.a
    return WorldPoint(intersect)
