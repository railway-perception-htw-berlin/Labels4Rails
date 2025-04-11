import abc
import enum
import dataclasses
from labels4rails import scene
from labels4rails import utils
from labels4rails.utils import config


from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsItem
from PyQt5.QtCore import QRectF


class AimRail(enum.Enum):
    """
    Possible rails to aim at.
    """

    LEFT = 0
    RIGHT = enum.auto()


@dataclasses.dataclass
class CrossHairCircle:
    """
    Properties defining a circle with crosshair int the center.
    """

    left_line: tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]
    top_line: tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]
    right_line: tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]
    bottom_line: tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]
    center: utils.geometry.IImagePoint
    radius: int


class ITrackStencil(metaclass=abc.ABCMeta):
    """
    Calculate properties of a track stencil aiming device.
    """


    @abc.abstractmethod
    def __init__(
        self,
        cfg: config.TrackStencil,
        camera: utils.camera.ICamera,
    ) -> None:
        """
        :param cfg: Configuration data class
        :param camera: Image to world calculator
        """
        pass

    def incr_angle(self, degrees: int) -> None:
        """
        Increment track stencil angle.
        :param degrees: Degrees to increment
        """
        pass

    def incr_width(self, width: int) -> None:
        """
        Increment track stencil width.
        :param width: Pixels to increment
        """
        pass

    @property
    @abc.abstractmethod
    def aim_rail(self) -> AimRail:
        pass

    @property
    @abc.abstractmethod
    def left_circle(self) -> CrossHairCircle:
        pass

    @property
    @abc.abstractmethod
    def right_circle(self) -> CrossHairCircle:
        pass

    @property
    @abc.abstractmethod
    def center_line(
        self,
    ) -> tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]:
        pass

    @abc.abstractmethod
    def toggle(self):
        """
        Toggle rail to aim on.
        """
        pass

    @abc.abstractmethod
    def refresh(self, position: utils.geometry.ImagePoint) -> None:
        """
        Recalculate properties.
        :param position: Center point of aim device
        """
        pass


class TrackStencil(ITrackStencil):
    """
    Calculate properties of a track stencil aiming device.
    """

    def __init__(
        self,
        cfg: config.TrackStencil,
        camera: utils.camera.ICamera,
    ) -> None:
        """
        :param cfg: Configuration data class
        :param camera: Image to world calculator
        """
        self._aim_rail: AimRail = AimRail.LEFT
        self._cfg: config.TrackStencil = cfg
        self._camera: utils.camera.ICamera = camera
        self._left_circle: CrossHairCircle
        self._left_circle = self._circle(utils.geometry.ImagePoint(0, 0), 1)
        self._right_circle: CrossHairCircle
        self._right_circle = self._circle(utils.geometry.ImagePoint(0, 0), 1)
        self._center_line: tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]
        self._center_line = (
            utils.geometry.ImagePoint(0, 0),
            utils.geometry.ImagePoint(0, 0),
        )
        self._left_point: utils.geometry.ImagePoint
        self._left_point = utils.geometry.ImagePoint(0, 0)
        self._right_point: utils.geometry.ImagePoint
        self._right_point = utils.geometry.ImagePoint(0, 0)
        self._width_correction: int = 0
        self._angle_correction: int = 0
        self._label_mode = "independent_mode"

    def incr_angle(self, degrees: int) -> None:
        """
        Increment track stencil angle.
        :param degrees: Degrees to increment
        """
        self._angle_correction += degrees

    def incr_width(self, width: int) -> None:
        """
        Increment track stencil width.
        :param width: Pixels to increment
        """
        self._width_correction += width

    @property
    def label_mode(self):
        return self._label_mode

    @label_mode.setter
    def label_mode(self, value):
        self._label_mode = value

    @property
    def aim_rail(self) -> AimRail:
        return self._aim_rail

    @property
    def track_mark(self) -> scene.target.ITrackMark:
        return scene.target.TrackMark([self.left_point, self.right_point])

    @property
    def left_point(self) -> utils.geometry.IImagePoint:
        return self._left_point

    @property
    def right_point(self) -> utils.geometry.IImagePoint:
        return self._right_point

    @property
    def left_circle(self) -> CrossHairCircle:
        return self._left_circle

    @property
    def right_circle(self) -> CrossHairCircle:
        return self._right_circle

    @property
    def center_line(
        self,
    ) -> tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]:
        return self._center_line

    def toggle(self):
        """
        Toggle rail to aim on.
        """
        if self._aim_rail == AimRail.LEFT:
            self._aim_rail = AimRail.RIGHT
        else:
            self._aim_rail = AimRail.LEFT

    def refresh(self, position: utils.geometry.IImagePoint) -> None:
        """
        Recalculate properties.
        :param position: Center point of aim device
        """
        if self.label_mode == "side_point":
            # Rail width at given position
            ip: utils.geometry.IImagePoint = self._camera.point_from_distance(
                position, self._cfg.rail_width, "x"
            )
            rail_width_image: int
            rail_width_image = abs(ip.x - position.x) if abs(ip.x - position.x) >= 1 else 1

            if self._aim_rail == AimRail.LEFT:
                self._left_point = position
                self._left_circle = self._circle(position, rail_width_image // 2)
                right_position: utils.geometry.IImagePoint
                right_point = self._camera.point_from_distance(
                    position,
                    self._cfg.track_width + self._cfg.rail_width,
                    "x",
                )
                right_point = utils.geometry.ImagePoint(
                    right_point.x + self._width_correction, right_point.y
                )
                self._right_point = utils.geometry.rotate(
                    self._angle_correction,
                    position,
                    right_point,
                )
                self._right_circle = self._circle(self._right_point, rail_width_image // 2)
                self._center_line = (position, self._right_point)
            elif self._aim_rail == AimRail.RIGHT:
                self._right_point = position
                self._right_circle = self._circle(position, rail_width_image // 2)
                left_position: utils.geometry.IImagePoint
                left_point = self._camera.point_from_distance(
                    position,
                    -self._cfg.track_width - self._cfg.rail_width ,
                    "x",
                )
                left_point = utils.geometry.ImagePoint(
                    left_point.x - self._width_correction, left_point.y
                )
                self._left_point = utils.geometry.rotate(
                    self._angle_correction,
                    position,
                    left_point,
                )
                self._left_circle = self._circle(self._left_point, rail_width_image // 2)
                self._center_line = (position, self._left_point)
        else:
            # Rail width at given position
            ip: utils.geometry.IImagePoint = self._camera.point_from_distance(
                position, self._cfg.rail_width, "x"
            )
            rail_width_image: int
            rail_width_image = abs(ip.x - position.x) if abs(ip.x - position.x) >= 1 else 1

            left_point = utils.geometry.ImagePoint(0, 0)
            self._right_point = position
            self._right_circle = self._circle(position, rail_width_image // 2)

            self._left_point = self._right_point
            self._left_circle = self._right_circle

    def _circle(
        self,
        center: utils.geometry.IImagePoint,
        radius: int,
    ) -> CrossHairCircle:
        """
        Calculate properties of circle with crosshair.
        :param center: Center of circle
        :param radius: Radius of circle
        :return: Property data class
        """
        buffer: int
        buffer = self._cfg.hair_to_midpoint_distance
        buffer = buffer if radius > buffer else radius

        # Cross hair left line
        left_line_left_point: utils.geometry.IImagePoint
        left_line_left_point = utils.geometry.ImagePoint(center.x - radius, center.y)
        left_line_right_point: utils.geometry.IImagePoint
        left_line_right_point = utils.geometry.ImagePoint(center.x - buffer, center.y)
        left_line: tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]
        left_line = (left_line_left_point, left_line_right_point)

        # Cross hair top line
        top_line_left_point: utils.geometry.IImagePoint
        top_line_left_point = utils.geometry.ImagePoint(center.x, center.y - radius)
        top_line_right_point: utils.geometry.IImagePoint
        top_line_right_point = utils.geometry.ImagePoint(center.x, center.y - buffer)
        top_line: tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]
        top_line = (top_line_left_point, top_line_right_point)

        # Cross hair right line
        right_line_left_point: utils.geometry.IImagePoint
        right_line_left_point = utils.geometry.ImagePoint(center.x + buffer, center.y)
        right_line_right_point: utils.geometry.IImagePoint
        right_line_right_point = utils.geometry.ImagePoint(center.x + radius, center.y)
        right_line: tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]
        right_line = (right_line_left_point, right_line_right_point)

        # Cross hair bottom line
        bottom_line_left_point: utils.geometry.IImagePoint
        bottom_line_left_point = utils.geometry.ImagePoint(center.x, center.y + buffer)
        bottom_line_right_point: utils.geometry.IImagePoint
        bottom_line_right_point = utils.geometry.ImagePoint(center.x, center.y + radius)
        bottom_line: tuple[utils.geometry.IImagePoint, utils.geometry.IImagePoint]
        bottom_line = (bottom_line_left_point, bottom_line_right_point)

        cross_hair_circle = CrossHairCircle(
            left_line, top_line, right_line, bottom_line, center, radius
        )
        return cross_hair_circle


class QtCircleAimdevice(QGraphicsEllipseItem):
    def __init__(self, x: float, y: float, w: float, h: float):
        super(QtCircleAimdevice, self).__init__(x, y, w, h)
