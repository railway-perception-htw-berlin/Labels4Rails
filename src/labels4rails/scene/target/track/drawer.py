from typing import Union, Optional
import abc
import enum
from labels4rails import utils
from . import rail
from .track import ITrack, TrackPosition
import numpy as np
import numpy.typing as npt
import cv2

from PyQt5.QtGui import (
    QPen,
    QColor,
    QPainterPath,
    QPolygonF,
)
from PyQt5.QtWidgets import QGraphicsPathItem
from PyQt5.QtCore import QPointF


class TrackBedDrawOptions(enum.Enum):
    """
    Possible attributes of trackbed to draw.
    """

    CONTOUR = 0
    FILL = enum.auto()


class ITrackDrawer(metaclass=abc.ABCMeta):
    """
    Draw track bed.
    """

    @abc.abstractmethod
    def __init__(self) -> None:
        pass

    @abc.abstractmethod
    def draw(
        self,
        image: npt.NDArray[np.uint8],
        track: ITrack,
        camera: utils.camera.ICamera,
        cfg: utils.config.Tracks,
        *args: Union[rail.RailDrawOptions, TrackBedDrawOptions],
        drawing_element: Optional[str] = None
    ) -> None:
        """
        Draw switch on image.
        :param image: Image to draw on
        :param track: Track object
        :param camera: Image to world calculator
        :param cfg: Configuration data class
        :param args: Attributes of track to draw
        """
        pass

    @abc.abstractmethod
    def draw_rails(
        self,
        image: npt.NDArray[np.uint8],
        left_rail: rail.IRail,
        right_rail: rail.IRail,
        cfg: utils.config.Rail,
        camera: utils.camera.ICamera,
        *args: Union[rail.RailDrawOptions, TrackBedDrawOptions],
    ) -> npt.NDArray[np.uint8]:
        """
        Draw rail on image
        :param image: Image to draw on
        :param right_rail: Rail object
        :param left_rail: Rail object
        :param camera: Image to world calculator
        :param cfg: Configuration data class
        :return: Image with rail
        """
        pass

    @staticmethod
    @abc.abstractmethod
    def draw_track_bed(
        image: npt.NDArray[np.uint8],
        left_rail: rail.IRail,
        right_rail: rail.IRail,
        cfg: utils.config.TrackBed,
        camera: utils.camera.ICamera,
        *args: TrackBedDrawOptions,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw track bed on image.
        :param image: Image to draw on
        :param left_rail: Rail object
        :param right_rail: Rail object
        :param cfg: Configuration data class
        :param camera: Image to world calculator
        :param args: Attributes to draw
        :return: Image with track bed
        """
        pass


class OpenCVTrackDrawer(ITrackDrawer):
    """
    Draw track bed.
    """

    def __init__(self):
        self.rail_drawer = rail.OpenCVRailDrawer()

    def draw(
        self,
        image: npt.NDArray[np.uint8],
        track: ITrack,
        camera: utils.camera.ICamera,
        cfg: utils.config.Tracks,
        *args: Union[rail.RailDrawOptions, TrackBedDrawOptions],
        drawing_element: Optional[str] = None
    ) -> None:
        """
        Draw switch on image.
        :param image: Image to draw on
        :param track: Track object
        :param camera: Image to world calculator
        :param cfg: Configuration data class
        :param args: Attributes of track to draw
        """
        if track.position == TrackPosition.EGO:

            if track.selected is False:
                cfg_track: config.Track = cfg.ego
                cfg_track_bed: config.TrackBed = cfg.ego.track_bed
            else:
                cfg_track: config.Track = cfg.selected
                cfg_track_bed: config.TrackBed = cfg.selected.track_bed


        elif track.position == TrackPosition.LEFT:

            if track.selected is False:
                cfg_track = cfg.left
                cfg_track_bed = cfg.left.track_bed
            else:
                cfg_track = cfg.selected
                cfg_track_bed = cfg.selected.track_bed

        elif track.position == TrackPosition.RIGHT:

            if track.selected is False:
                cfg_track = cfg.right
                cfg_track_bed = cfg.right.track_bed
            else:
                cfg_track = cfg.selected
                cfg_track_bed = cfg.selected.track_bed



        else:
            raise ValueError("Expected valid TrackPosition.")
        if drawing_element == None or drawing_element == "rails":
            self.draw_rails(
                image, track.left_rail, track.right_rail, camera, cfg_track, *args
            )
        if drawing_element == None or drawing_element == "track_bed":
            self.draw_track_bed(
                image, track.left_rail, track.right_rail, camera, cfg_track_bed, *args
            )

    def draw_rails(
        self,
        image: npt.NDArray[np.uint8],
        left_rail: rail.IRail,
        right_rail: rail.IRail,
        camera: utils.camera.ICamera,
        cfg: utils.config.Track,
        *args: rail.RailDrawOptions,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw rail on image
        :param image: Image to draw on
        :param right_rail: Rail object
        :param left_rail: Rail object
        :param camera: Image to world calculator
        :param cfg: Configuration data class
        :return: Image with rail
        """
        if rail.RailDrawOptions.FILL in args:
            self.rail_drawer.draw_fill(right_rail, cfg.left_rail, image, camera)
            self.rail_drawer.draw_fill(left_rail, cfg.right_rail, image, camera)
            
        if rail.RailDrawOptions.CONTOUR in args:
            self.rail_drawer.draw_contour(right_rail, cfg.left_rail, image, camera)
            self.rail_drawer.draw_contour(left_rail, cfg.right_rail, image, camera)
            
        if rail.RailDrawOptions.SPLINES in args:
            self.rail_drawer.draw_splines(right_rail, cfg.left_rail, image, camera)
            self.rail_drawer.draw_splines(left_rail, cfg.right_rail, image, camera)

        if rail.RailDrawOptions.MARKS in args:
            self.rail_drawer.draw_marks(right_rail, cfg.left_rail, image, camera)
            self.rail_drawer.draw_marks(left_rail, cfg.right_rail, image, camera)

        return image

    def draw_track_bed(
        self,
        image: npt.NDArray[np.uint8],
        left_rail: rail.IRail,
        right_rail: rail.IRail,
        camera: utils.camera.ICamera,
        cfg: utils.config.TrackBed,
        *args: TrackBedDrawOptions,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw track bed on image.
        :param image: Image to draw on
        :param left_rail: Rail object
        :param right_rail: Rail object
        :param cfg: Configuration data class
        :param camera: Image to world calculator
        :param args: Attributes to draw
        :return: Image with track bed
        """
        contour_points_left: list[utils.geometry.IImagePoint]
        contour_points_left = left_rail.contour_points_splines_right(
            camera, cfg.interpolation_steps
        )
        contour_points_left = sorted(contour_points_left, reverse=False)

        contour_points_right: list[utils.geometry.IImagePoint]
        contour_points_right = right_rail.contour_points_splines_left(
            camera, cfg.interpolation_steps
        )
        contour_points_right = sorted(contour_points_right, reverse=True)

        contour_points: list[utils.geometry.IImagePoint]
        contour_points = [*contour_points_left, *contour_points_right]

        if len(contour_points) > 0:
            if contour_points[0].pointAtImageBottom(image.shape[0]) and contour_points[-1].pointAtImageSide(image.shape[1]):
                if contour_points[-1].pointAtImageLeftSide():
                    contour_points.append(utils.geometry.ImagePoint(0, image.shape[0]))
                else:
                    contour_points.append(utils.geometry.ImagePoint(image.shape[1], image.shape[0]))
            elif contour_points[-1].pointAtImageBottom(image.shape[0]) and contour_points[0].pointAtImageSide(image.shape[1]):
                if contour_points[0].pointAtImageLeftSide():
                    contour_points.append(utils.geometry.ImagePoint(0, image.shape[0]))
                else:
                    contour_points.append(utils.geometry.ImagePoint(image.shape[1], image.shape[0]))

        if TrackBedDrawOptions.CONTOUR in args:
            # Opencv has BGR order
            color = [cfg.contour_color[i] for i in [2, 1, 0]]
            contour_points_arr: list = []
            for contour_point in contour_points:
                contour_points_arr.append(contour_point.point)
            cv2.polylines(
                image, np.array([contour_points_arr]), True, color=color, thickness=1
            )

        if TrackBedDrawOptions.FILL in args:
            # Opencv has BGR order
            color = [cfg.fill_color[i] for i in [2, 1, 0]]
            contour_points_arr: list = []
            for contour_point in contour_points:
                contour_points_arr.append(contour_point.point)
            if contour_points_arr:
                cv2.fillConvexPoly(image, np.array(contour_points_arr), color=color)

        return image

class QtTrackDrawer(ITrackDrawer):
    """
    Draw track bed.
    """

    def __init__(self):
        self.rail_drawer = rail.drawer.QtRailDrawer()

    def draw(
        self,
        image: npt.NDArray[np.uint8],
        track: ITrack,
        camera: utils.camera.ICamera,
        cfg: utils.config.Tracks,
        qt_scene,
        *args: Union[rail.RailDrawOptions, TrackBedDrawOptions],
        drawing_element: Optional[str] = None
    ) -> None:
        """
        Draw switch on image.
        :param image: Image to draw on
        :param track: Track object
        :param camera: Image to world calculator
        :param cfg: Configuration data class
        :param args: Attributes of track to draw
        """
        if track.position == TrackPosition.EGO:

            if track.selected is False:
                cfg_track: config.Track = cfg.ego
                cfg_track_bed: config.TrackBed = cfg.ego.track_bed
            else:
                cfg_track: config.Track = cfg.selected
                cfg_track_bed: config.TrackBed = cfg.selected.track_bed


        elif track.position == TrackPosition.LEFT:

            if track.selected is False:
                cfg_track = cfg.left
                cfg_track_bed = cfg.left.track_bed
            else:
                cfg_track = cfg.selected
                cfg_track_bed = cfg.selected.track_bed

        elif track.position == TrackPosition.RIGHT:

            if track.selected is False:
                cfg_track = cfg.right
                cfg_track_bed = cfg.right.track_bed
            else:
                cfg_track = cfg.selected
                cfg_track_bed = cfg.selected.track_bed



        else:
            raise ValueError("Expected valid TrackPosition.")
        if drawing_element == None or drawing_element == "rails":
            self.draw_rails(
                image, track.left_rail, track.right_rail, camera, cfg_track, qt_scene, *args
            )
        if drawing_element == None or drawing_element == "track_bed":
            self.draw_track_bed(
                image, track.left_rail, track.right_rail, camera, cfg_track_bed, qt_scene, *args
            )

    def draw_rails(
        self,
        image: npt.NDArray[np.uint8],
        left_rail: rail.IRail,
        right_rail: rail.IRail,
        camera: utils.camera.ICamera,
        cfg: utils.config.Track,
        qt_scene,
        *args: rail.RailDrawOptions,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw rail on image
        :param image: Image to draw on
        :param right_rail: Rail object
        :param left_rail: Rail object
        :param camera: Image to world calculator
        :param cfg: Configuration data class
        :return: Image with rail
        """
        if rail.RailDrawOptions.FILL in args:
            self.rail_drawer.draw_fill(right_rail, cfg.right_rail, image, camera, qt_scene)
            self.rail_drawer.draw_fill(left_rail, cfg.left_rail, image, camera, qt_scene)
            
        if rail.RailDrawOptions.CONTOUR in args:
            self.rail_drawer.draw_contour(right_rail, cfg.right_rail, image, camera, qt_scene)
            self.rail_drawer.draw_contour(left_rail, cfg.left_rail, image, camera, qt_scene)
            
        if rail.RailDrawOptions.SPLINES in args:
            self.rail_drawer.draw_splines(right_rail, cfg.right_rail, image, camera, qt_scene)
            self.rail_drawer.draw_splines(left_rail, cfg.left_rail, image, camera, qt_scene)

        if rail.RailDrawOptions.MARKS in args:
            self.rail_drawer.draw_marks(right_rail, cfg.right_rail, image, camera, qt_scene)
            self.rail_drawer.draw_marks(left_rail, cfg.left_rail, image, camera, qt_scene)

        return image

    def draw_track_bed(
        self,
        image: npt.NDArray[np.uint8],
        left_rail: rail.IRail,
        right_rail: rail.IRail,
        camera: utils.camera.ICamera,
        cfg: utils.config.TrackBed,
        qt_scene,
        *args: TrackBedDrawOptions,
    ) -> npt.NDArray[np.uint8]:
        """
        Draw track bed on image.
        :param image: Image to draw on
        :param left_rail: Rail object
        :param right_rail: Rail object
        :param cfg: Configuration data class
        :param camera: Image to world calculator
        :param args: Attributes to draw
        :return: Image with track bed
        """
        contour_points_left: list[utils.geometry.IImagePoint]
        contour_points_left = left_rail.contour_points_splines_right(
            camera, cfg.interpolation_steps
        )
        contour_points_left = sorted(contour_points_left, reverse=False)

        contour_points_right: list[utils.geometry.IImagePoint]
        contour_points_right = right_rail.contour_points_splines_left(camera, cfg.interpolation_steps)
        if contour_points_right[0].y > contour_points_right[-1].y:
            contour_points_right = contour_points_right[::-1]

        contour_points: list[utils.geometry.IImagePoint]
        contour_points = [*contour_points_left, *contour_points_right]

        if len(contour_points) > 0:
            if contour_points[0].pointAtImageBottom(image.shape[0]) and contour_points[-1].pointAtImageSide(image.shape[1]):
                if contour_points[-1].pointAtImageLeftSide():
                    contour_points.append(utils.geometry.ImagePoint(0, image.shape[0]))
                else:
                    contour_points.append(utils.geometry.ImagePoint(image.shape[1], image.shape[0]))
            elif contour_points[-1].pointAtImageBottom(image.shape[0]) and contour_points[0].pointAtImageSide(image.shape[1]):
                if contour_points[0].pointAtImageLeftSide():
                    contour_points.append(utils.geometry.ImagePoint(0, image.shape[0]))
                else:
                    contour_points.append(utils.geometry.ImagePoint(image.shape[1], image.shape[0]))




        pen = QPen()

        if TrackBedDrawOptions.CONTOUR in args:
            col_arr = [cfg.contour_color[i] for i in [2, 1, 0]]
            pen_color = QColor(col_arr[2], col_arr[1], col_arr[0])
            color = QColor('transparent')
            contour_points_arr: list[QPointF] = []
            contour_points_arr: list[QPointF] = [QPointF(contour_point.point[0], contour_point.point[1]) for contour_point in contour_points]

            path: QPainterPath = QPainterPath()
            polylines: QPolygonF()

            pen.setStyle(1)
            pen.setColor(pen_color)
            polylines = QPolygonF(contour_points_arr)
            path.addPolygon(polylines)

            target = QGraphicsPathItem(path, None)
            qt_scene.get_annotation_group().addToGroup(target)
            target.setPen(pen)
            target.setBrush(color)
        
        if TrackBedDrawOptions.FILL in args:
            col_arr = [cfg.fill_color[i] for i in [2, 1, 0]]
            color = QColor(col_arr[2], col_arr[1], col_arr[0])
            contour_points_arr: list[QPointF] = []
            contour_points_arr: list[QPointF] = [QPointF(contour_point.point[0], contour_point.point[1]) for contour_point in contour_points]

            path: QPainterPath = QPainterPath()
            polylines: QPolygonF()

            pen.setStyle(1)
            pen.setColor(color)
            polylines = QPolygonF(contour_points_arr)
            path.addPolygon(polylines)

            target = QGraphicsPathItem(path, None)
            qt_scene.get_annotation_group().addToGroup(target)
            target.setPen(pen)
            target.setBrush(color)
