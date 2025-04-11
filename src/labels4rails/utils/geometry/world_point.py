from __future__ import annotations
from typing import Union
import abc
import numpy as np
import numpy.typing as npt


class IWorldPoint(metaclass=abc.ABCMeta):
    """
    Represent point in 3D world space.
    """

    @abc.abstractmethod
    def __init__(self, *args: Union[npt.ArrayLike, int, float]) -> None:
        """
        Coordinates of WorldPoint as numpy-array or x, y and z coordinate.
        :param args: Numpy array or x, y and z coordinate.
        """
        pass

    @property
    @abc.abstractmethod
    def x(self) -> np.int64:
        pass

    @property
    @abc.abstractmethod
    def y(self) -> np.int64:
        pass

    @property
    @abc.abstractmethod
    def z(self) -> np.int64:
        pass

    @property
    @abc.abstractmethod
    def point(self) -> npt.NDArray[np.int64]:
        pass

    @abc.abstractmethod
    def __eq__(self, other: object) -> bool:
        pass

    @abc.abstractmethod
    def __hash__(self) -> int:
        pass


class WorldPoint(IWorldPoint):
    """
    Point in 3D-World
    """

    def __init__(self, *args: Union[npt.ArrayLike, int, float]) -> None:
        """
        Coordinates of WorldPoint as numpy-array or x, y and z coordinate.
        :param args: Numpy array or x, y and z coordinate.
        """
        self._point: npt.NDArray[np.int64] = np.array([0, 0, 0]).astype(int)

        if len(args) == 1 and isinstance(args[0], np.ndarray):
            if args[0].shape != (3,):
                msg: str = f"Expected shape to be (3,), got {args[0].shape}"
                raise ValueError(msg)
            else:
                # Image point is integer, describing a pixel
                np.rint(args[0], out=self._point, casting="unsafe")
        elif len(args) == 3:
            self._point = np.rint(np.array([*args])).astype(int)
        else:
            msg = f"Expected ether 1 argument or 3, got {len(args)}"
            raise ValueError(msg)

    @property
    def x(self) -> np.int64:
        return self._point[0]

    @property
    def y(self) -> np.int64:
        return self._point[1]

    @property
    def z(self) -> np.int64:
        return self._point[2]

    @property
    def point(self) -> npt.NDArray[np.int64]:
        return self._point

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorldPoint):
            raise NotImplementedError
        return bool(self.x == other.x and self.y == other.y and self.z == other.z)

    def __hash__(self) -> int:
        return hash((self.x, self.y, self.z))
