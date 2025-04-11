import abc
from labels4rails import utils


class ITrackMark(metaclass=abc.ABCMeta):
    """
    Represent rail mark consisting of two marks.
    """

    @property
    @abc.abstractmethod
    def mark(self) -> list[utils.geometry.IImagePoint, utils.geometry.IImagePoint]:
        pass

    @property
    @abc.abstractmethod
    def left_mark(self) -> utils.geometry.IImagePoint:
        pass

    @property
    @abc.abstractmethod
    def right_mark(self) -> utils.geometry.IImagePoint:
        pass


class TrackMark(ITrackMark):
    """
    Represent rail mark consisting of two marks.
    """

    def __init__(
        self,
        mark: list[utils.geometry.IImagePoint, utils.geometry.IImagePoint],
    ):
        """
        :param mark: Rail mark
        """
        self._mark: list[utils.geometry.IImagePoint, utils.geometry.IImagePoint] = mark

    @property
    def mark(self) -> list[utils.geometry.IImagePoint, utils.geometry.IImagePoint]:
        return self._mark

    @property
    def left_mark(self) -> utils.geometry.IImagePoint:
        return self._mark[0]

    @property
    def right_mark(self) -> utils.geometry.IImagePoint:
        return self._mark[1]
