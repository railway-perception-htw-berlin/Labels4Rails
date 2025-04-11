from typing import Union
import abc
from .world_point import IWorldPoint
import numpy as np


class IPlane(metaclass=abc.ABCMeta):
    """
    Represent a plane
    """

    def __init__(
        self,
        c: IWorldPoint,
        r: Union[np.float_, float],
    ) -> None:
        """
        :param c:
        :param r:
        """

    @property
    @abc.abstractmethod
    def c(self) -> IWorldPoint:
        pass

    @property
    @abc.abstractmethod
    def r(self) -> np.float_:
        pass


class Plane(IPlane):
    """
    Represent a plane
    """

    def __init__(
        self,
        c: IWorldPoint,
        r: Union[np.float_, float],
    ) -> None:
        """
        :param c:
        :param r:
        """
        self._c: IWorldPoint = c
        self._r: np.float_ = np.float_(r)

    @property
    def c(self) -> IWorldPoint:
        return self._c

    @property
    def r(self) -> np.float_:
        return self._r
