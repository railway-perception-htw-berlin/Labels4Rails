from typing import Union, Sequence
import functools
from . import IImagePoint, ImagePoint
import numpy as np
import numpy.typing as npt


def CatmullRomSpline(P0, P1, P2, P3, nPoints=100):
    """
    P0, P1, P2, and P3 should be (x,y) point pairs that define the Catmull-Rom spline.
    nPoints is the number of points to include in this curve segment.
    This implementation is from Wikipedia (https://en.wikipedia.org/w/index.php?title=Centripetal_Catmull%E2%80%93Rom_spline&oldid=988076930#Code_example_in_Python)
    Last accessed 05.08.2022
    """
    # Convert the points to numpy so that we can do array multiplication
    P0, P1, P2, P3 = map(np.array, [P0, P1, P2, P3])

    # Parametric constant: 0.5 for the centripetal spline, 0.0 for the uniform spline, 1.0 for the chordal spline.
    alpha = 0.5
    # Premultiplied power constant for the following tj() function.
    alpha = alpha / 2

    def tj(ti, Pi, Pj):
        xi, yi = Pi
        xj, yj = Pj
        return ((xj - xi) ** 2 + (yj - yi) ** 2) ** alpha + ti

    # Calculate t0 to t4
    t0 = 0
    t1 = tj(t0, P0, P1)
    t2 = tj(t1, P1, P2)
    t3 = tj(t2, P2, P3)

    # Only calculate points between P1 and P2
    t = np.linspace(t1, t2, nPoints)

    # Reshape so that we can multiply by the points P0 to P3
    # and get a point for each value of t.
    t = t.reshape(len(t), 1)
    A1 = (t1 - t) / (t1 - t0) * P0 + (t - t0) / (t1 - t0) * P1
    A2 = (t2 - t) / (t2 - t1) * P1 + (t - t1) / (t2 - t1) * P2
    A3 = (t3 - t) / (t3 - t2) * P2 + (t - t2) / (t3 - t2) * P3

    B1 = (t2 - t) / (t2 - t0) * A1 + (t - t0) / (t2 - t0) * A2
    B2 = (t3 - t) / (t3 - t1) * A2 + (t - t1) / (t3 - t1) * A3

    C = (t2 - t) / (t2 - t1) * B1 + (t - t1) / (t2 - t1) * B2
    return C


def CatmullRomChain(P, steps):
    """
    Calculate Catmull–Rom for a chain of points and return the combined curve.
    This implementation is from Wikipedia (https://en.wikipedia.org/w/index.php?title=Centripetal_Catmull%E2%80%93Rom_spline&oldid=988076930#Code_example_in_Python)
    Last accessed 05.08.2022
    """
    sz = len(P)

    # The curve C will contain an array of (x, y) points.
    C = []
    for i in range(sz - 3):
        c = CatmullRomSpline(P[i], P[i + 1], P[i + 2], P[i + 3], steps)
        C.extend(c)

    return C


@functools.cache
def calculate_splines(
        points: Union[Sequence[IImagePoint]],
        steps: int,
) -> list[IImagePoint]:
    """
    Calculate splines in between given Sequence of ImagePoints.
    :param points: Sequence of image points
    :param steps: Interpolation steps inbetween and including two points
    :return: List of interpolated ImagePoints
    """

    if len(points) > 1:
        points_arr: npt.NDArray[np.int_]
        points_arr = np.vstack([point.point for point in points])
        # helper points for calculation
        last = np.repeat([points_arr[-1]], repeats=1, axis=0)
        first = np.repeat([points_arr[0]], repeats=1, axis=0)

        last[0][1] = last[0][1] + 1
        first[0][1] = first[0][1] + 1

        points_arr = np.vstack([points_arr, last])
        points_arr = np.vstack([first, points_arr])

        c = CatmullRomChain(points_arr, steps)

        x_new, y_new = zip(*c)
        spline_points = []
        for x, y in zip(x_new, y_new):
            spline_point: IImagePoint
            spline_point = ImagePoint(
                x,
                y,
            )
            spline_points.append(spline_point)
        return spline_points
    else:
        return []
