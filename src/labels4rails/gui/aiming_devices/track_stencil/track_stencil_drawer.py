import abc
from labels4rails.utils import config
from .track_stencil import ITrackStencil, CrossHairCircle
import numpy as np
import numpy.typing as npt
import cv2
from labels4rails import utils
from labels4rails.scene.target.track import Track

# cv: line, circle
# qt: line/pathgraphictiem, ellipse 
from PyQt5.QtGui import (
    QPen,
    QColor
    )
from labels4rails.gui.aiming_devices.track_stencil.track_stencil import QtCircleAimdevice


class ITrackStencilDrawer(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def draw(
        self,
        image: npt.NDArray[np.uint8],
        stencil: ITrackStencil,
        cfg: config.TrackStencil,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw track stencil.
        :param image: Image to draw on
        :param stencil: Stencil class
        :param cfg: Configuration data class
        :return: Image with track stencil drawn on
        """
        pass


class OpenCVTrackStencilDrawer(ITrackStencilDrawer):
    def draw(
        self,
        image: npt.NDArray[np.uint8],
        stencil: ITrackStencil,
        cfg: config.TrackStencil,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw track stencil.
        :param image: Image to draw on
        :param stencil: Stencil class
        :param cfg: Configuration data class
        :return: Image with track stencil drawn on
        """
        image = self._draw_circle(image, stencil.left_circle, cfg)
        image = self._draw_circle(image, stencil.right_circle, cfg)
        return image

    @staticmethod
    def _draw_circle(
        image: npt.NDArray[np.uint8],
        circle: CrossHairCircle,
        cfg: config.TrackStencil,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw circle of track stencil.
        :param image: Image to draw on
        :param circle: Circle attributes data class
        :param cfg: Configuration data class
        :return: Image with circle drawn on
        """
        color: list[int, int, int]
        color = [cfg.color[i] for i in [2, 1, 0]]  # Opencv has BGR order
        thickness: int
        thickness = int(cfg.thickness * image.shape[0])
        
        thickness = thickness if thickness >= 1 else 1
        cv2.line(
            image,
            circle.left_line[0].point,
            circle.left_line[1].point,
            color,
            thickness,
        )
        cv2.line(
            image, circle.top_line[0].point, circle.top_line[1].point, color, thickness
        )
        cv2.line(
            image,
            circle.right_line[0].point,
            circle.right_line[1].point,
            color,
            thickness,
        )
        cv2.line(
            image,
            circle.bottom_line[0].point,
            circle.bottom_line[1].point,
            color,
            thickness,
        )
        cv2.circle(image, circle.center.point, circle.radius, color, thickness)
        return image

    @staticmethod
    def _draw_line(stencil: ITrackStencil):
        """
        Draw lin in between circles.
        """
        pass


class QtTrackStencilDrawer(ITrackStencilDrawer):
    def draw(
        self,
        image: npt.NDArray[np.uint8],
        stencil: ITrackStencil,
        cfg: config.TrackStencil,
        qt_scene,
        position,
            drag_color,
            flag: bool,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw track stencil.
        :param image: Image to draw on
        :param stencil: Stencil class
        :param cfg: Configuration data class

        :return: Image with track stencil drawn on
        :param flag: bool if position is near a mark of the current selected track
        :param drag_color: color to signal that the aiming device is on a mark.
        :param position: position of the aiming device
        """

        qt_scene.del_aim_device()

        image = self._draw_circle(image, stencil.left_circle, cfg, qt_scene, position, 'left', drag_color,flag)
        image = self._draw_circle(image, stencil.right_circle, cfg, qt_scene, position, 'right', drag_color,flag)
        return image 
    
    @staticmethod
    def _draw_circle(
        image: npt.NDArray[np.uint8],
        circle: CrossHairCircle,
        cfg: config.TrackStencil,
        qt_scene,
        m_position,
            stencilinfo,
            drag_color,
            flag: bool

    ) -> npt.NDArray[np.uint8]:
        """
        Draw circle of track stencil.
        :param image: Image to draw on
        :param circle: Circle attributes data class
        :param cfg: Configuration data class
        :param active_track: current active track to check if the aiming device is on a mark
        :param drag_color: color to signal that the aiming device is on a mark.
        :return: Image with circle drawn on
        """


        pen = QPen(1)
        col_arr = [cfg.color[i] for i in [2, 1, 0]]
        color: list[int, int, int]
        color = QColor(col_arr[2], col_arr[1], col_arr[0])

        if flag:
            color = QColor(drag_color[0], drag_color[1], drag_color[2])

        thickness: int
        thickness = int(cfg.thickness * image.shape[0])
        width: int = circle.radius
        width = 1 if not width else width # make thickness at least 1px
        thickness = thickness if thickness >= 1 else 1

        pen.setColor(color)
        pen.setWidth(thickness)
        if circle.radius == 0:
            pen.setStyle(0)

        target = QtCircleAimdevice(0, 0, width, width)
        target.setPen(pen)
        target.setBrush(color)
        target.setPos(m_position.x - width//2, m_position.y - width//2)
        qt_scene.get_aim_device_group().addToGroup(target)
        if stencilinfo == 'left': 
            qt_scene.set_aim_device_a(target)
            return image
        if stencilinfo == 'right': 
            qt_scene.set_aim_device_b(target)
            return image    
        
    def update(
        self, 
        stencil: ITrackStencil,
        qt_scene,
        ) -> None:

        circle_l = stencil.left_circle
        circle_r = stencil.right_circle
        width: int = circle_l.radius
        width = 1 if not width else width # make thickness at least 1px

        qt_scene.get_aim_device_a().setPos(circle_l.center.point[0] - width/2, circle_l.center.point[1] - width/2)
        qt_scene.get_aim_device_b().setPos(circle_r.center.point[0] - width/2, circle_r.center.point[1] - width/2)
        
    @staticmethod
    def _draw_line(stencil: ITrackStencil):
        """
        Draw lin in between circles.
        """
        pass
