from typing import Optional
import abc
import enum
from labels4rails import utils
from .switch import ISwitch, SwitchKind, SwitchDirection
import numpy as np
import numpy.typing as npt
import cv2


from PyQt5.QtGui import (
    QPen,
    QColor,
    QFont
    )
from PyQt5.QtWidgets import (
    QGraphicsEllipseItem, 
    QGraphicsRectItem, 
    QGraphicsTextItem,
    )
from PyQt5.QtCore import QPoint


class SwitchDrawOptions(enum.Enum):
    """
    Possible attributes of switches to draw.
    """

    MARKS = 0
    BOUNDING_BOX = enum.auto()
    TEXT_LABEL = enum.auto()


class ISwitchDrawer(metaclass=abc.ABCMeta):
    """
    Draw switch.
    """

    @staticmethod
    @abc.abstractmethod
    def draw(
        image: npt.NDArray[np.uint8],
        switch_: ISwitch,
        cfg: utils.config.Switches,
        aim_point: Optional[utils.geometry.IImagePoint],
        *args,
    ) -> None:
        """
        Draw switch on image.
        :param image: Image to draw on
        :param switch_: Switch object
        :param cfg: Configuration data class
        :param aim_point: Where aime device points to
        :param args: Attributes of switch to draw
        """
        pass


class OpenCVSwitchDrawer(ISwitchDrawer):
    """
    Switch drawer implemented using OpenCV.
    """

    def draw(
        self,
        image: npt.NDArray[np.uint8],
        switch_: ISwitch,
        cfg: utils.config.Switches,
        *args: SwitchDrawOptions,
        aim_point: Optional[utils.geometry.IImagePoint] = None,
    ) -> None:
        """
        Draw switch on image.
        :param image: Image to draw on
        :param switch_: Switch object
        :param cfg: Configuration data class
        :param aim_point: Where aime device points to
        :param args: Attributes of switch to draw
        """
        if (
            switch_.kind == SwitchKind.FORK
            and switch_.direction == SwitchDirection.LEFT
        ):
            if switch_.selected is False:
                box_color = cfg.fork.left.box_color
            else:
                box_color = cfg.unknown.selected.box_color
            marks_color = cfg.fork.left.marks_color

        elif (
            switch_.kind == SwitchKind.FORK
            and switch_.direction == SwitchDirection.RIGHT
        ):

            if switch_.selected is False:
                box_color = cfg.fork.right.box_color
            else:
                box_color = cfg.unknown.selected.box_color

            marks_color = cfg.fork.right.marks_color
        elif (
            switch_.kind == SwitchKind.FORK
            and switch_.direction == SwitchDirection.UNKNOWN
        ):
            if switch_.selected is False:
                box_color = cfg.fork.unknown.box_color
            else:
                box_color = cfg.unknown.selected.box_color

            marks_color = cfg.fork.unknown.marks_color

        elif (
            switch_.kind == SwitchKind.MERGE
            and switch_.direction == SwitchDirection.LEFT
        ):
            if switch_.selected is False:
                box_color = cfg.merge.left.box_color
            else:
                box_color = cfg.unknown.selected.box_color

            marks_color = cfg.merge.left.marks_color

        elif (
            switch_.kind == SwitchKind.MERGE
            and switch_.direction == SwitchDirection.UNKNOWN
        ):
            if switch_.selected is False:
                box_color = cfg.merge.unknown.box_color
            else:
                box_color = cfg.unknown.selected.box_color
            marks_color = cfg.merge.unknown.marks_color

        elif (
            switch_.kind == SwitchKind.UNKNOWN
            and switch_.direction == SwitchDirection.LEFT
        ):
            if switch_.selected is False:
                box_color = cfg.unknown.left.box_color
            else:
                box_color = cfg.unknown.selected.box_color
            marks_color = cfg.unknown.left.marks_color
        elif (
            switch_.kind == SwitchKind.UNKNOWN
            and switch_.direction == SwitchDirection.RIGHT
        ):
            if switch_.selected is False:
                box_color = cfg.unknown.right.box_color
            else:
                box_color = cfg.unknown.selected.box_color
            marks_color = cfg.unknown.right.marks_color
        else:
            if switch_.selected is False:
                box_color = cfg.merge.right.box_color
            else:
                box_color = cfg.unknown.selected.box_color
            marks_color = cfg.merge.right.marks_color

        if SwitchDrawOptions.MARKS in args:
            self._draw_marks(image, switch_, marks_color)
        if SwitchDrawOptions.BOUNDING_BOX in args:
            self._draw_bounding_box(image, switch_, box_color, aim_point)
        if SwitchDrawOptions.TEXT_LABEL in args:
            self._draw_text_label(image, switch_, box_color)

    @staticmethod
    def _draw_marks(
        image: npt.NDArray[np.uint8],
        switch_: ISwitch,
        marks_color: tuple[int, int, int],
    ) -> None:
        """
        Draw marks describing bounding box.
        :param image: Image to draw on
        :param switch_: Switch object
        :param marks_color: Color of marks
        """
        marks_color = [marks_color[i] for i in [2, 1, 0]]  # Opencv has BGR order
        mark: utils.geometry.IImagePoint
        for mark in switch_.marks:
            cv2.circle(
                image,
                mark.point,
                5,
                color=marks_color,
                thickness=-1,
            )

    @staticmethod
    def _draw_text_label(
        image: npt.NDArray[np.uint8],
        switch_: ISwitch,
        text_color: tuple[int, int, int],
    ) -> None:
        """
        Draw attributes as text label to identify switch object in
        scene image.
        :param image: Image to draw on
        :param switch_: Switch object
        :param text_color: Color of text label
        """
        text_color = [text_color[i] for i in [2, 1, 0]]  # Opencv has BGR order
        text_label_point: npt.NDArray[np.int_]
        if len(switch_.marks) == 1:
            text_label_point = switch_.marks[0].point
            cv2.putText(
                img=image,
                text=str(switch_),
                org=text_label_point,
                fontFace=0,
                fontScale=1.0,
                color=text_color,
                thickness=2,
                lineType=cv2.LINE_AA,
            )
        elif len(switch_.marks) == 2:
            if switch_.marks[0] > switch_.marks[1]:
                text_label_point = switch_.marks[0].point
            else:
                text_label_point = switch_.marks[1].point
            cv2.putText(
                img=image,
                text=str(switch_),
                org=text_label_point,
                fontFace=0,
                fontScale=1.0,
                color=text_color,
                thickness=2,
                lineType=cv2.LINE_AA,
            )

    @staticmethod
    def _draw_bounding_box(
        image: npt.NDArray[np.uint8],
        switch_: ISwitch,
        box_color: tuple[int, int, int],
        aim_point: Optional[utils.geometry.IImagePoint] = None,
    ) -> None:
        """
        Draw bounding box.
        :param image: Image to draw on
        :param switch_: Switch object
        :param box_color: Color of bounding box
        :param aim_point: Where aime device points to
        """
        box_color = [box_color[i] for i in [2, 1, 0]]  # Opencv has BGR order
        if len(switch_.marks) == 1 and aim_point is not None:
            cv2.rectangle(
                image,
                switch_.marks[0].point,
                aim_point.point,
                box_color,
                2,
            )
        elif len(switch_.marks) == 2:
            cv2.rectangle(
                image,
                switch_.marks[0].point,
                switch_.marks[1].point,
                box_color,
                2,
            )


class QtSwitchDrawer(ISwitchDrawer):
    """
    Switch drawer implemented using OpenCV.
    """

    def draw(
        self,
        image: npt.NDArray[np.uint8],
        switch_: ISwitch,
        cfg: utils.config.Switches,
        qt_scene,
        *args: SwitchDrawOptions,
        aim_point: Optional[utils.geometry.IImagePoint] = None,
    ) -> None:
        """
        Draw switch on image.
        :param image: Image to draw on
        :param switch_: Switch object
        :param cfg: Configuration data class
        :param aim_point: Where aime device points to
        :param args: Attributes of switch to draw
        """
        if (
            switch_.kind == SwitchKind.FORK
            and switch_.direction == SwitchDirection.LEFT
        ):
            if switch_.selected is False:
                box_color = cfg.fork.left.box_color
            else:
                box_color = cfg.unknown.selected.box_color
            marks_color = cfg.fork.left.marks_color

        elif (
            switch_.kind == SwitchKind.FORK
            and switch_.direction == SwitchDirection.RIGHT
        ):

            if switch_.selected is False:
                box_color = cfg.fork.right.box_color
            else:
                box_color = cfg.unknown.selected.box_color

            marks_color = cfg.fork.right.marks_color
        elif (
            switch_.kind == SwitchKind.FORK
            and switch_.direction == SwitchDirection.UNKNOWN
        ):
            if switch_.selected is False:
                box_color = cfg.fork.unknown.box_color
            else:
                box_color = cfg.unknown.selected.box_color

            marks_color = cfg.fork.unknown.marks_color

        elif (
            switch_.kind == SwitchKind.MERGE
            and switch_.direction == SwitchDirection.LEFT
        ):
            if switch_.selected is False:
                box_color = cfg.merge.left.box_color
            else:
                box_color = cfg.unknown.selected.box_color

            marks_color = cfg.merge.left.marks_color

        elif (
            switch_.kind == SwitchKind.MERGE
            and switch_.direction == SwitchDirection.UNKNOWN
        ):
            if switch_.selected is False:
                box_color = cfg.merge.unknown.box_color
            else:
                box_color = cfg.unknown.selected.box_color
            marks_color = cfg.merge.unknown.marks_color

        elif (
            switch_.kind == SwitchKind.UNKNOWN
            and switch_.direction == SwitchDirection.LEFT
        ):
            if switch_.selected is False:
                box_color = cfg.unknown.left.box_color
            else:
                box_color = cfg.unknown.selected.box_color
            marks_color = cfg.unknown.left.marks_color
        elif (
            switch_.kind == SwitchKind.UNKNOWN
            and switch_.direction == SwitchDirection.RIGHT
        ):
            if switch_.selected is False:
                box_color = cfg.unknown.right.box_color
            else:
                box_color = cfg.unknown.selected.box_color
            marks_color = cfg.unknown.right.marks_color
        else:
            if switch_.selected is False:
                box_color = cfg.merge.right.box_color
            else:
                box_color = cfg.unknown.selected.box_color
            marks_color = cfg.merge.right.marks_color

        if SwitchDrawOptions.MARKS in args:
            self._draw_marks(image, switch_, marks_color, qt_scene)
        if SwitchDrawOptions.BOUNDING_BOX in args:
            self._draw_bounding_box(image, switch_, box_color, qt_scene, aim_point)
        if SwitchDrawOptions.TEXT_LABEL in args:
            self._draw_text_label(image, switch_, box_color, qt_scene)

    @staticmethod
    def _draw_marks(
        image: npt.NDArray[np.uint8],
        switch_: ISwitch,
        marks_color: tuple[int, int, int],
        qt_scene,
    ) -> None:
        """
        Draw marks describing bounding box.
        :param image: Image to draw on
        :param switch_: Switch object
        :param marks_color: Color of marks
        """
        pen = QPen(0)
        col_arr = [marks_color[i] for i in [2, 1, 0]]
        color = QColor(col_arr[2], col_arr[1], col_arr[0])
        mark: utils.geometry.IImagePoint
        width: int = 5

        for mark in switch_.marks:
            target = QGraphicsEllipseItem(0, 0, width, width)
            qt_scene.get_annotation_group().addToGroup(target)
            target.setPen(pen)
            target.setBrush(color)
            target.setPos(mark.point[0] - width/2, mark.point[1] - width/2)
        
    @staticmethod
    def _draw_text_label(
        image: npt.NDArray[np.uint8],
        switch_: ISwitch,
        text_color: tuple[int, int, int],
        qt_scene,
    ) -> None:
        """
        Draw attributes as text label to identify switch object in
        scene image.
        :param image: Image to draw on
        :param switch_: Switch object
        :param text_color: Color of text label
        """

        col_arr = [text_color[i] for i in [2, 1, 0]]
        text_color = QColor(col_arr[2], col_arr[1], col_arr[0])
        text_label_point: npt.NDArray[np.int_]
        font = QFont("Sans Serif", 7)

        if len(switch_.marks) == 1:
            text_label_point = switch_.marks[0].point
            target = QGraphicsTextItem(str(switch_))
            qt_scene.get_annotation_group().addToGroup(target)
            target.setFont(font)
            target.setDefaultTextColor(text_color)
            target.setPos(text_label_point[0], text_label_point[1])
        elif len(switch_.marks) == 2:
            if switch_.marks[0] > switch_.marks[1]:
                text_label_point = switch_.marks[0].point
            else:
                text_label_point = switch_.marks[1].point
            target = QGraphicsTextItem(str(switch_))
            qt_scene.get_annotation_group().addToGroup(target)
            target.setFont(font)
            target.setDefaultTextColor(text_color)
            target.setPos(text_label_point[0], text_label_point[1])

    @staticmethod
    def _draw_bounding_box(
        image: npt.NDArray[np.uint8],
        switch_: ISwitch,
        box_color: tuple[int, int, int],
        qt_scene,
        aim_point: Optional[utils.geometry.IImagePoint] = None,
    ) -> None:
        """
        Draw bounding box.
        :param image: Image to draw on
        :param switch_: Switch object
        :param box_color: Color of bounding box
        :param aim_point: Where aime device points to
        """
        pen = QPen(1)
        col_arr = [box_color[i] for i in [2, 1, 0]]
        pen_color = QColor(col_arr[2], col_arr[1], col_arr[0])
        item_color = QColor('transparent')

        if switch_.marks:
            pen.setColor(pen_color)
        if len(switch_.marks) == 1 and aim_point is not None:
            # this case is for drawing first point of rect -> using ellipse
            width = 4 

            target = QGraphicsEllipseItem(0, 0, width, width)
            qt_scene.get_annotation_group().addToGroup(target)
            target.setPen(pen)
            target.setBrush(item_color)       
            target.setPos(
                switch_.marks[0].point[0] - width/2,
                switch_.marks[0].point[1] - width/2
                )
        elif len(switch_.marks) == 2:
            w = switch_.marks[1].point[0] - switch_.marks[0].point[0]
            h = switch_.marks[1].point[1] - switch_.marks[0].point[1]

            target = QGraphicsRectItem(0, 0, w, h)
            qt_scene.get_annotation_group().addToGroup(target)
            target.setPen(pen)
            target.setBrush(item_color)       
            target.setPos(
                switch_.marks[0].point[0],
                switch_.marks[0].point[1]
                )