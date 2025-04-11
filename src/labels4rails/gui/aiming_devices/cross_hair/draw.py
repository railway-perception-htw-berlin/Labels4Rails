from abc import ABCMeta, abstractmethod
from .cross_hair import ICrossHair
from labels4rails.utils import config
import numpy as np
import numpy.typing as npt
import cv2

from PyQt5.QtGui import (
    QPen,
    QColor
    )
from labels4rails.gui.aiming_devices.cross_hair.cross_hair import QtCrossAimdeviceLine

class ICrossHairDrawer(metaclass=ABCMeta):
    @staticmethod
    @abstractmethod
    def draw(
        image: npt.NDArray[np.uint8],
        cross_hair: ICrossHair,
        cfg: config.CrossHair,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw crosshair on image.
        :param image: Image to draw on
        :param cross_hair: CrossHair object
        :param cfg: Configuration data class
        :return: Image with drawn crosshair
        """
        pass

class OpenCVCrossHairDrawer(ICrossHairDrawer):
    @staticmethod
    def draw(
        image: npt.NDArray[np.uint8],
        cross_hair: ICrossHair,
        cfg: config.CrossHair,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw crosshair on image.
        :param image: Image to draw on
        :param cross_hair: CrossHair object
        :param cfg: Configuration data class
        :return: Image with drawn crosshair
        """
        thickness: int = round(cfg.thickness * image.shape[0])
        radius: int = round(cfg.mid_point_radius * image.shape[0])
        color: list[int, int, int]
        i: int
        color = [cfg.color[i] for i in [2, 1, 0]]  # Opencv has BGR order
        cv2.line(
            image,
            cross_hair.left[0].point,
            cross_hair.left[1].point,
            color,
            thickness,
        )
        cv2.line(
            image,
            cross_hair.right[0].point,
            cross_hair.right[1].point,
            color,
            thickness,
        )
        cv2.line(
            image,
            cross_hair.top[0].point,
            cross_hair.top[1].point,
            color,
            thickness,
        )
        cv2.line(
            image,
            cross_hair.bottom[0].point,
            cross_hair.bottom[1].point,
            color,
            thickness,
        )
        cv2.circle(
            image,
            cross_hair.center.point,
            radius,
            color=color,
            thickness=thickness,
        )
        return image

class QtCrossHairDrawer(ICrossHairDrawer):
    def draw(
        self,
        image: npt.NDArray[np.uint8],
        cross_hair: ICrossHair,
        cfg: config.CrossHair,
        qt_scene,
        position
    ) -> npt.NDArray[np.uint8]:
        """
        Draw crosshair on image.
        :param image: Image to draw on
        :param cross_hair: CrossHair object
        :param cfg: Configuration data class
        :return: Image with drawn crosshair
        """

        qt_scene.del_aim_device()

        image = self._draw_line(image, cross_hair, cfg, qt_scene, position, 'horizontal')
        image = self._draw_line(image, cross_hair, cfg, qt_scene, position, 'vertical')
        return image

    @staticmethod
    def _draw_line(
        image: npt.NDArray[np.uint8],
        cross_hair: ICrossHair,
        cfg: config.CrossHair,
        qt_scene,
        position,
        lineinfo) -> None:

        pen = QPen(1)
        col_arr = [cfg.color[i] for i in [2, 1, 0]]
        color: list[int, int, int]
        color = QColor(col_arr[2], col_arr[1], col_arr[0])
        thickness: int = round(cfg.thickness * image.shape[0])
        radius: int = round(cfg.mid_point_radius * image.shape[0])


        # no dynamic length of cross hair lines
        if lineinfo == 'vertical':
            target = QtCrossAimdeviceLine(
                0,
                0,
                0,
                image.shape[0]*2
            )
        elif lineinfo == 'horizontal':
            target = QtCrossAimdeviceLine(
                0,
                0,
                image.shape[1]*2,
                0
            )

        pen.setColor(color)
        pen.setWidth(thickness)
        target.setPen(pen)
        qt_scene.get_aim_device_group().addToGroup(target)

        if lineinfo == 'vertical':
            target.setPos(
                position.x, 
                position.y - target.line().length()/2
                )
            qt_scene.set_aim_device_a(target)
            return image
        if lineinfo == 'horizontal':
            target.setPos(
                position.x - target.line().length()/2,
                position.y
                )
            qt_scene.set_aim_device_b(target)
            return image

    def update(self) -> None:
        pass
