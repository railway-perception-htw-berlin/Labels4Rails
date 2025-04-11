from typing import Union, Optional
import abc
import functools
from labels4rails import utils
from labels4rails import data
import numpy as np
import numpy.typing as npt

# qt: use nparray conversion

class ICamera(metaclass=abc.ABCMeta):
    """
    Camera to convert points in 2D space representing a point on the
    image plane to 3D space in the real world and vice versa.
    """

    @abc.abstractmethod
    def world_to_pixel(
        self,
        world_point: utils.geometry.IWorldPoint,
    ) -> utils.geometry.IImagePoint:
        """
        Calculate a point on the 2D coordinates in the  projection plane
        on the Image.
        :param world_point: World point in 3D space
        :return: Image coordinates ind 2D space
        """
        pass

    @abc.abstractmethod
    def pixel_to_world(
        self,
        image_point: utils.geometry.IImagePoint,
        plane: Optional[utils.geometry.IPlane] = None,
    ) -> utils.geometry.IWorldPoint:
        """
        Calculate a point in the real world in 3D space from a given
        point on the 2D projection image coordinates.
        Because this calculation is ambiguous, a plane must be
        specified onto which this point is projected.
        :param image_point: Point on 2D image
        :param plane: Plan in 3D space / real world
        :return: World coordinates in 3D space
        """
        pass

    @abc.abstractmethod
    def point_from_distance(
        self,
        image_point: utils.geometry.IImagePoint,
        distance: Union[float, np.float_],
        direction: str,
    ) -> utils.geometry.IImagePoint:
        """
        Calculate a point in image coordinates which has a certain
        distance to another point.
        The distance is given in mm and refers to an axis in world
        coordinates.
        :param image_point: Point on 2D image
        :param distance: Distance in mm - 3D space
        :param direction: Axis in 3D space
        :return: Point on 2D image
        """
        pass


class Camera(ICamera):
    def __init__(self, calib_data: data.ICameraReader) -> None:
        """
        :param calib_data: Information about camera
        """
        self.roll: npt.NDArray[np.float_]
        self.roll = np.radians(calib_data.roll)
        self.pitch: npt.NDArray[np.float_]
        self.pitch = np.radians(calib_data.pitch)
        self.yaw: npt.NDArray[np.float_]
        self.yaw = np.radians(calib_data.yaw)
        self.center: npt.NDArray[np.float_]
        self.center = np.squeeze(calib_data.tvec)
        self.camera_matrix: npt.NDArray[np.float_]
        self.camera_matrix = calib_data.camera_matrix
        self._rotation_matrix: npt.NDArray[np.float_]
        self._rotation_matrix: Optional[npt.NDArray[np.float_]] = None
        self._projection_matrix: npt.NDArray[np.float_]
        self._projection_matrix: Optional[npt.NDArray[np.float_]] = None
        self._origin: Optional[npt.NDArray[np.float_]] = None

        self._calculate_rotation_matrix()
        self._calculate_projection_matrix()

    def _calculate_rotation_matrix(self) -> None:
        """
        Calculate rotation of the image projection plane relative to
        the plane in 3D world space.
        """
        # Rotation on y-axis
        r_yaw = np.array(
            [
                [np.cos(self.yaw), 0, -np.sin(self.yaw)],
                [0, 1, 0],
                [np.sin(self.yaw), 0, np.cos(self.yaw)],
            ]
        )
        # Rotation on x-axis
        r_pitch = np.array(
            [
                [1, 0, 0],
                [0, np.cos(self.pitch), np.sin(self.pitch)],
                [0, -np.sin(self.pitch), np.cos(self.pitch)],
            ]
        )
        # Rotation on z-axis
        r_roll = np.array(
            [
                [np.cos(self.roll), np.sin(self.roll), 0],
                [-np.sin(self.roll), np.cos(self.roll), 0],
                [0, 0, 1],
            ]
        )
        # Combined rotation matrix
        self._rotation_matrix = np.dot(np.dot(r_roll, r_pitch), r_yaw)

    def _calculate_projection_matrix(self) -> None:
        """ """
        rotation_matrix = self._rotation_matrix
        origin = self._world_to_camera(np.array([0, 0, 0]))
        origin = np.expand_dims(origin, axis=0)
        stacked = np.hstack((rotation_matrix, origin.T))
        extrinsic_matrix = np.dot(self.camera_matrix, stacked)
        self._projection_matrix = extrinsic_matrix

    def _world_to_camera(self, w) -> npt.NDArray[np.float_]:
        """ """
        return np.dot(self._rotation_matrix, (w - self.center))

    @functools.cache
    def world_to_pixel(
        self,
        world_point: utils.geometry.IWorldPoint,
    ) -> utils.geometry.IImagePoint:
        """
        Calculate a point on the 2D coordinates in the  projection plane
        on the Image.
        :param world_point: World point in 3D space
        :return: Image coordinates ind 2D space
        """
        projection = self._projection_matrix
        world_point1 = np.ones((1, 4), dtype=float)
        world_point1[0][:3] = world_point.point
        uv1 = np.dot(projection, world_point1.T)
        uv = np.zeros(2)
        uv[0] = uv1[0] / uv1[2] if uv1[2] > 0 else float("NaN")
        uv[1] = uv1[1] / uv1[2] if uv1[2] > 0 else float("NaN")
        return utils.geometry.ImagePoint(uv)

    @functools.cache
    def pixel_to_world(
        self,
        image_point: utils.geometry.IImagePoint,
        plane: utils.geometry.IPlane = utils.geometry.Plane(
            utils.geometry.WorldPoint(np.array([0, 1, 0])), 0
        ),
    ) -> utils.geometry.IWorldPoint:
        """
        Calculate a point in the real world in 3D space from a given
        point on the 2D projection image coordinates.
        Because this calculation is ambiguous, a plane must be
        specified onto which this point is projected.
        :param image_point: Point on 2D image
        :param plane: Plan in 3D space / real world
        :return: World coordinates in 3D space
        """
        uv = image_point
        # Invert == Transpose, because rotation matrix is orthogonal
        rotation_invert = self._rotation_matrix.T

        # Pixel coordinates
        uv1 = np.array([uv.x, uv.y, 1], dtype=float)
        # Camera coordinates
        line_of_sight_cam = np.dot(np.linalg.inv(self.camera_matrix), uv1)
        # World coordinates
        line_of_sight = np.dot(rotation_invert, line_of_sight_cam)
        camera_center = self.center
        line: utils.geometry.Line
        line = utils.geometry.Line(camera_center, line_of_sight)
        world_point: utils.geometry.IWorldPoint
        world_point = utils.geometry.intersection(plane, line)

        return world_point

    @functools.cache
    def point_from_distance(
        self,
        image_point: utils.geometry.IImagePoint,
        distance: Union[float, np.float_],
        direction: str,
    ) -> utils.geometry.IImagePoint:
        """
        Calculate a point in image coordinates which has a certain
        distance to another point.
        The distance is given in mm and refers to an axis in world
        coordinates.
        :param image_point: Point on 2D image
        :param distance: Distance in mm - 3D space
        :param direction: Axis in 3D space
        :return: Point on 2D image
        """
        world_point: utils.geometry.IWorldPoint = self.pixel_to_world(image_point)
        if direction == "x":
            world_point = utils.geometry.WorldPoint(
                world_point.x + distance, world_point.y, world_point.z
            )
        elif direction == "y":
            world_point = utils.geometry.WorldPoint(
                world_point.x, world_point.y + distance, world_point.z
            )
        elif direction == "z":
            world_point = utils.geometry.WorldPoint(
                world_point.x, world_point.y, world_point.z + distance
            )
        else:
            msg: str = f"Expected direction to be in ['x', 'y', 'z'], got {direction}"
            raise ValueError(msg)
        # Point beyond image horizon
        if world_point.z < 0:
            return image_point
        else:
            return self.world_to_pixel(world_point)
