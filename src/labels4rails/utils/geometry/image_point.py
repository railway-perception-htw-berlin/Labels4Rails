from __future__ import annotations
from typing import Union
import abc
import functools
import numpy as np
import numpy.typing as npt


@functools.total_ordering
class IImagePoint(metaclass=abc.ABCMeta):
    """
    Represent a 2D point on an image.
    """

    @property
    @abc.abstractmethod
    def x(self) -> np.int64:
        pass

    @x.setter
    @abc.abstractmethod
    def x(self, x: Union[np.int_, np.float_, float]) -> None:
        pass

    @property
    @abc.abstractmethod
    def y(self) -> np.int64:
        pass

    @y.setter
    @abc.abstractmethod
    def y(self, y: Union[np.int_, np.float_, float]) -> None:
        pass

    @property
    @abc.abstractmethod
    def point(self) -> npt.NDArray[np.int64]:
        pass

    @abc.abstractmethod
    def __eq__(self, other: IImagePoint) -> bool:
        pass

    @abc.abstractmethod
    def __lt__(self, other: IImagePoint) -> bool:
        pass

    @abc.abstractmethod
    def __hash__(self) -> int:
        pass

    @abc.abstractmethod
    def midpoint(self, other: IImagePoint) -> IImagePoint:
        pass

    @abc.abstractmethod
    def pointAtImageBottom(self, image_height: np.int_) -> bool:
        pass
    
    @abc.abstractmethod
    def pointAtImageSide(self, image_width: np.int_) -> bool:
        pass

    @abc.abstractmethod
    def pointAtImageLeftSide(self) -> bool:
        pass

    @abc.abstractmethod
    def pointAtImageRightSide(self, image_width: np.int_) -> bool:
        pass


@functools.total_ordering
class ImagePoint(IImagePoint):
    """
    Represent a 2D point on an image.
    """

    def __init__(self, *args: Union[npt.ArrayLike, int, float]) -> None:
        """
        Coordinates of ImagePoint as numpy-array or x and y coordinate.
        :param args: Numpy array or x and y coordinate.
        """
        self._point: npt.NDArray[np.int64] = np.array([0, 0], dtype=int)

        if len(args) == 1 and isinstance(args[0], np.ndarray):
            if args[0].shape != (2,):
                msg: str = f"Expected shape to be (2,), got {args[0].shape}"
                raise ValueError(msg)
            else:
                # Image point is integer, describing a pixel
                self._point = args[0].astype(int)
        elif len(args) == 2:
            np.rint(np.array([*args]), out=self._point, casting="unsafe")
        else:
            msg = f"Expected ether 1 argument or 2, got {len(args)}"
            raise ValueError(msg)

    @property
    def x(self) -> np.int64:
        return self._point[0]

    @property
    def y(self) -> np.int64:
        return self._point[1]

    @property
    def point(self) -> npt.NDArray[np.int64]:
        return self._point

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ImagePoint):
            raise NotImplementedError
        return bool(self.x == other.x and self.y == other.y)

    def __lt__(self, other: IImagePoint) -> bool:
        return bool(self.y > other.y)

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def midpoint(self, other: IImagePoint) -> IImagePoint:
        mid_arr: npt.NDArray(np.float_)
        mid_arr = np.mean((self._point, other.point), axis=0)
        return self.__class__(mid_arr)

    def pointAtImageBottom(self, image_height: np.int_) -> bool:
        return self.y > image_height-11
    
    def pointAtImageSide(self, image_width: np.int_) -> bool:
        return self.pointAtImageLeftSide() or self.pointAtImageRightSide(image_width)

    def pointAtImageLeftSide(self) -> bool:
        return self.x < 10

    def pointAtImageRightSide(self, image_width: np.int_) -> bool:
        return self.x > image_width-11
