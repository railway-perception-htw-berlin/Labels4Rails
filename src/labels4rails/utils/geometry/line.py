import abc
import numpy.typing as npt
import numpy as np


class ILine(metaclass=abc.ABCMeta):
    """
    Represent line in 3D space.
    """

    @abc.abstractmethod
    def __init__(self, p: np.ndarray, a: np.ndarray) -> None:
        """
        :param p: Point in 3D space
        :param a: Point in 3D space
        """
        pass

    @property
    @abc.abstractmethod
    def p(self) -> npt.NDArray[np.float_]:
        pass

    @property
    @abc.abstractmethod
    def a(self) -> npt.NDArray[np.float_]:
        pass


class Line(ILine):
    """
    Represent line in 3D space.
    """

    def __init__(self, p: np.ndarray, a: np.ndarray) -> None:
        """
        :param p: Point in 3D space
        :param a: Point in 3D space
        """
        self._p: npt.NDArray[np.float_] = p
        self._a: npt.NDArray[np.float_] = a

    @property
    def p(self) -> npt.NDArray[np.float_]:
        return self._p

    @property
    def a(self) -> npt.NDArray[np.float_]:
        return self._a
