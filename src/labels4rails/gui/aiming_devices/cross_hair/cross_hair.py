import abc
from labels4rails import utils
from labels4rails.utils import config


from PyQt5.QtWidgets import QGraphicsItem, QGraphicsLineItem
from PyQt5.QtCore import QLineF
from PyQt5.QtGui import (
    QPen,
    QColor
    )
import numpy as np


class ICrossHair(metaclass=abc.ABCMeta):
    def __init__(self, cfg: config.CrossHair) -> None:
        """
        :param cfg: Configuration dict
        """
        pass

    @abc.abstractmethod
    def refresh(
        self,
        position: utils.geometry.IImagePoint,
        width: int,
        height: int,
    ) -> None:
        """
        Recalculate properties.
        :param position: Center point of aim device
        :param width: Total crosshair width in px
        :param height: Total crosshair width in px
        """
        pass

    @property
    @abc.abstractmethod
    def center(self) -> utils.geometry.IImagePoint:
        pass

    @property
    @abc.abstractmethod
    def left(self) -> tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]:
        pass

    @property
    @abc.abstractmethod
    def right(self) -> tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]:
        pass

    @property
    @abc.abstractmethod
    def top(self) -> tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]:
        pass

    @property
    @abc.abstractmethod
    def bottom(self) -> tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]:
        pass


class CrossHair(ICrossHair):
    """
    Implements bounding box crosshair.
    """

    def __init__(self, cfg: config.CrossHair) -> None:
        """
        :param cfg: Configuration dict
        """
        # Relative buffer to absolute buffer
        self._cfg: config.CrossHair = cfg
        self._left: tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]
        self._left = (utils.geometry.ImagePoint(0, 0), utils.geometry.ImagePoint(0, 0))
        self._right: tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]
        self._right = (utils.geometry.ImagePoint(0, 0), utils.geometry.ImagePoint(0, 0))
        self._top: tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]
        self._top = (utils.geometry.ImagePoint(0, 0), utils.geometry.ImagePoint(0, 0))
        self._bottom: tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]
        self._bottom = (
            utils.geometry.ImagePoint(0, 0),
            utils.geometry.ImagePoint(0, 0),
        )
        self._center = utils.geometry.IImagePoint
        self._center = utils.geometry.ImagePoint(0, 0)

    def refresh(
        self,
        position: utils.geometry.IImagePoint,
        width: int,
        height: int,
    ) -> None:
        """
        Recalculate properties.
        :param position: Center point of aim device
        :param width: Total crosshair width in px
        :param height: Total crosshair width in px
        """
        buffer = round(width * self._cfg.mid_point_buffer)
        self._left = (
            utils.geometry.ImagePoint(0, position.y),
            utils.geometry.ImagePoint(position.x - buffer, position.y),
        )
        self._right = (
            utils.geometry.ImagePoint(position.x + buffer, position.y),
            utils.geometry.ImagePoint(width, position.y),
        )
        self._top = (
            utils.geometry.ImagePoint(position.x, 0),
            utils.geometry.ImagePoint(position.x, position.y - buffer),
        )
        self._bottom = (
            utils.geometry.ImagePoint(position.x, position.y + buffer),
            utils.geometry.ImagePoint(position.x, height),
        )
        self._center = position

    @property
    def points(self) -> list[utils.geometry.IImagePoint]:
        return [self._center]

    @property
    def center(self) -> utils.geometry.IImagePoint:
        return self._center

    @property
    def left(self) -> tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]:
        return self._left

    @property
    def right(self) -> tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]:
        return self._right

    @property
    def top(self) -> tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]:
        return self._top

    @property
    def bottom(self) -> tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]:
        return self._bottom


class QtCrossAimdeviceLine(QGraphicsLineItem):
    def __init__(self, x0, y0, x1, y1):
        super(QGraphicsLineItem, self).__init__(x0, y0, x1, y1)
