from .image_point import IImagePoint, ImagePoint
import numpy as np
import numpy.typing as npt


def rotate(
    angle: int,
    rotate_around: IImagePoint,
    point: IImagePoint,
) -> IImagePoint:
    """
    Rotate IImagePoint around another IImagePoint in 2D-space.
    :param angle: Angle to rotate
    :param rotate_around: Fix point
    :param point: Point to rotate
    :return: Rotated point
    """
    ra: npt.NDArray[np.float_] = rotate_around.point.astype(float)
    pt: npt.NDArray[np.float_] = point.point.astype(float)

    s = np.sin(np.deg2rad(angle))
    c = np.cos(np.deg2rad(angle))

    p = np.array([0, 0])
    p[0] = pt[0] - ra[0]
    p[1] = pt[1] - ra[1]

    r = np.array([0, 0])
    r[0] = p[0] * c - p[1] * s
    r[1] = p[0] * s + p[1] * c

    z = np.array([0, 0])
    z[0] = r[0] + ra[0]
    z[1] = r[1] + ra[1]
    return ImagePoint(z)
