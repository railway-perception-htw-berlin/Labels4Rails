import abc
import enum
from labels4rails import scene
from labels4rails import utils
from .rail import IRail
import numpy as np
import numpy.typing as npt
import cv2

from PyQt5.QtGui import (
    QPen,
    QColor,
    QPainterPath,
    QPolygonF,
)
from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem
from PyQt5.QtCore import QPointF


class RailDrawOptions(enum.Enum):
    """
    Possible attributes of rail to draw.
    """

    MARKS = 0
    SPLINES = enum.auto()
    CONTOUR = enum.auto()
    FILL = enum.auto()


class IRailDrawer(metaclass=abc.ABCMeta):
    """
    Draw rail.
    """

    @staticmethod
    @abc.abstractmethod
    def draw_marks(
        rail: IRail,
        cfg: utils.config.Rail,
        image: npt.NDArray[np.uint8],
        camera: utils.camera.ICamera,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw marks on image.
        :param rail: Rail to draw
        :param cfg: Configuration data class
        :param image: Image to draw on
        :param camera: Image to world calculator
        :return: Image with rail marks
        """
        pass

    @staticmethod
    @abc.abstractmethod
    def draw_splines(
        rail: IRail,
        cfg: utils.config.Rail,
        image: npt.NDArray[np.uint8],
        camera: utils.camera.ICamera,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw interpolated splines between marks on image.
        :param rail: Rail object
        :param cfg: Configuration data class
        :param image: Image to draw on
        :param camera: Image to world calculator
        :return: Image with splines
        """
        pass

    @staticmethod
    @abc.abstractmethod
    def draw_contour(
        rail: IRail,
        cfg: utils.config.Rail,
        image: npt.NDArray[np.uint8],
        camera: utils.camera.ICamera,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw contour of rail on image.
        :param rail: Rail to draw
        :param cfg: Configuration data class
        :param image: Image to draw on
        :param camera: Image to world calculator
        :return: Image with contour
        """
        pass

    @staticmethod
    @abc.abstractmethod
    def draw_fill(
        rail: IRail,
        cfg: utils.config.Rail,
        image: npt.NDArray[np.uint8],
        camera: utils.camera.ICamera,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw filled polygon of rail on image.
        :param rail: Rail to draw
        :param cfg: Configuration data class
        :param image: Image to draw on
        :param camera: Image to world calculator
        :return: Image with filled polygon
        """
        pass


class OpenCVRailDrawer(IRailDrawer):
    """
    Draw rail using OpenCV.
    """

    @staticmethod
    def draw_marks(
        rail: IRail,
        cfg: utils.config.Rail,
        image: npt.NDArray[np.uint8],
        camera: utils.camera.ICamera,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw marks on image.
        :param rail: Rail to draw
        :param cfg: Configuration data class
        :param image: Image to draw on
        :param camera: Image to world calculator
        :return: Image with rail marks
        """
        color = [cfg.marks_color[i] for i in [2, 1, 0]]  # Opencv has BGR order
        marks: list[utils.geometry.IImagePoint] = rail.marks
        widths: list[int] = rail.mark_points_image_widths(camera)
        mark: utils.geometry.IImagePoint
        width: int
        for mark, width in zip(marks, widths):
            cv2.circle(image, mark.point, width // 2, color=color, thickness=-1)
        # return data -> ('image', mark.point, width // 2, color=color, thickness=-1)
        return image

    @staticmethod
    def draw_splines(
        rail: IRail,
        cfg: utils.config.Rail,
        image: npt.NDArray[np.uint8],
        camera: utils.camera.ICamera,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw interpolated splines between marks on image.
        :param rail: Rail object
        :param cfg: Configuration data class
        :param image: Image to draw on
        :param camera: Image to world calculator
        :return: Image with splines
        """
        color = [cfg.splines_color[i] for i in [2, 1, 0]]  # Opencv has BGR order
        splines: list[utils.geometry.IImagePoint]
        splines = rail.spline_points(cfg.interpolation_steps)
        widths: list[int] = rail.spline_points_image_widths(
            camera, cfg.interpolation_steps
        )
        spline: utils.geometry.IImagePoint
        width: int
        for spline, width in zip(splines, widths):
            cv2.circle(image, spline.point, width // 2, color=color, thickness=-1)
        return image

    @staticmethod
    def draw_contour(
        rail: IRail,
        cfg: utils.config.Rail,
        image: npt.NDArray[np.uint8],
        camera: utils.camera.ICamera,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw contour of rail on image.
        :param rail: Rail to draw
        :param cfg: Configuration data class
        :param image: Image to draw on
        :param camera: Camera converting Image to World
        :return: Image with contour
        """
        color = [cfg.contour_color[i] for i in [2, 1, 0]]  # Opencv has BGR order
        contour_points: list[utils.geometry.IImagePoint]
        contour_points = rail.contour_points_splines(camera, cfg.interpolation_steps)
        contour_points_arr = [contour_point.point for contour_point in contour_points]
        if contour_points_arr:
            cv2.polylines(
                image,
                np.array([contour_points_arr]),
                True,
                color=color,
                thickness=1,
            )
        return image

    @staticmethod
    def draw_fill(
        rail: IRail,
        cfg: utils.config.Rail,
        image: npt.NDArray[np.uint8],
        camera: utils.camera.ICamera,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw filled polygon of rail on image.
        :param rail: Rail to draw
        :param cfg: Configuration data class
        :param image: Image to draw on
        :param camera: Image to world calculator
        :return: Image with filled polygon
        """
        color = [cfg.fill_color[i] for i in [2, 1, 0]]  # Opencv has BGR order
        contour_points: list[utils.geometry.IImagePoint]
        contour_points = rail.contour_points_splines(camera, cfg.interpolation_steps)
        contour_points_arr = [contour_point.point for contour_point in contour_points]
        if contour_points_arr:
            cv2.fillConvexPoly(
                image,
                np.array([contour_points_arr]),
                color=color,
            )
        return image


class QtRailDrawer(IRailDrawer):
    """
    Draw rail using OpenCV.
    """

    @staticmethod
    def draw_marks(
        rail: IRail,
        cfg: utils.config.Rail,
        image: npt.NDArray[np.uint8],
        camera: utils.camera.ICamera,
        qt_scene,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw marks on image.
        :param rail: Rail to draw
        :param cfg: Configuration data class
        :param image: Image to draw on
        :param camera: Image to world calculator
        :return: Image with rail marks
        """
        pen = QPen(1)
        col_arr = [cfg.marks_color[i] for i in [2, 1, 0]]
        color = QColor(col_arr[2], col_arr[1], col_arr[0])
        widths: list[int] = rail.mark_points_image_widths(camera)
        marks: list[utils.geometry.IImagePoint] = rail.marks

        pen.setColor(color)
        for point, width in zip(marks, widths):
            if width == 1:
                pen.setColor(QColor('transparent'))

            width = width if not width//2 else width//2 # make thickness at least 1px

            target = QGraphicsEllipseItem(0, 0, width, width)
            qt_scene.get_annotation_group().addToGroup(target)
            target.setPen(pen)
            target.setBrush(color)
            target.setPos(point.x - width/2, point.y - width/2)

    @staticmethod
    def draw_splines(
        rail: IRail,
        cfg: utils.config.Rail,
        image: npt.NDArray[np.uint8],
        camera: utils.camera.ICamera,
        qt_scene,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw interpolated splines between marks on image.
        :param rail: Rail object
        :param cfg: Configuration data class
        :param image: Image to draw on
        :param camera: Image to world calculator
        :return: Image with splines
        """

        pen = QPen(1)
        col_arr = [cfg.splines_color[i] for i in [2, 1, 0]]
        color = QColor(col_arr[2], col_arr[1], col_arr[0])
        splines: list[utils.geometry.IImagePoint]
        splines = rail.spline_points(cfg.interpolation_steps)
        widths: list[int] = rail.spline_points_image_widths(
            camera, 
            cfg.interpolation_steps
            )

        pen.setColor(color)
        for spline, width in zip(splines, widths):
            if width == 1:
                pen.setColor(QColor('transparent'))
            
            width = width if not width//2 else width//2 # make thickness at least 1px
            
            target = QGraphicsEllipseItem(0, 0, width, width)
            qt_scene.get_annotation_spline_group().addToGroup(target)
            target.setPen(pen)
            target.setBrush(color)
            target.setPos(spline.x - width/2, spline.y - width/2)
            
    @staticmethod
    def draw_contour(
        rail: IRail,
        cfg: utils.config.Rail,
        image: npt.NDArray[np.uint8],
        camera: utils.camera.ICamera,
        qt_scene,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw contour of rail on image.
        :param rail: Rail to draw
        :param cfg: Configuration data class
        :param image: Image to draw on
        :param camera: Camera converting Image to World
        :return: Image with contour
        """

        pen = QPen(1)
        col_arr = [cfg.contour_color[i] for i in [2, 1, 0]]  # Opencv has BGR order
        color = QColor('transparent')
        pen_color = QColor(col_arr[2], col_arr[1], col_arr[0])
        contour_points: list[utils.geometry.IImagePoint]
        contour_points = rail.contour_points_splines(camera, cfg.interpolation_steps)
        path: QPainterPath = QPainterPath()
        polylines: QPolygonF()

        pen.setColor(pen_color)
        contour_points_arr: list[QPointF] = [QPointF(contour_point.point[0], contour_point.point[1]) for contour_point in contour_points]

        if contour_points_arr:
            polylines = QPolygonF(contour_points_arr)
            path.addPolygon(polylines)
            target = QGraphicsPathItem(path, None)
            qt_scene.get_annotation_group().addToGroup(target)
            target.setPen(pen)
            target.setBrush(color)

    @staticmethod
    def draw_fill(
        rail: IRail,
        cfg: utils.config.Rail,
        image: npt.NDArray[np.uint8],
        camera: utils.camera.ICamera,
        qt_scene,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw filled polygon of rail on image.
        :param rail: Rail to draw
        :param cfg: Configuration data class
        :param image: Image to draw on
        :param camera: Image to world calculator
        :return: Image with filled polygon
        """

        pen = QPen(1)
        col_arr = [cfg.fill_color[i] for i in [2, 1, 0]]
        color = QColor(col_arr[2], col_arr[1], col_arr[0])
        contour_points: list[utils.geometry.IImagePoint]
        contour_points = rail.contour_points_splines(camera, cfg.interpolation_steps)
        contour_points_arr: list[QPointF] = [QPointF(contour_point.point[0], contour_point.point[1]) for contour_point in contour_points]
        path: QPainterPath = QPainterPath()
        polylines: QPolygonF()
        
        pen.setColor(color)
        if contour_points_arr:
            polylines = QPolygonF(contour_points_arr)
            path.addPolygon(polylines)
            target = QGraphicsPathItem(path, None)
            qt_scene.get_annotation_group().addToGroup(target)
            target.setPen(pen)
            target.setBrush(color)
