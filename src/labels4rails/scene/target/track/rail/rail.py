from typing import Optional
import abc
import enum
from labels4rails import utils
import numpy as np
import math


class RailSide(enum.IntEnum):
    """
    Possible side of a rail.
    """

    LEFT: int = -1
    RIGHT: int = 1


class IRail(metaclass=abc.ABCMeta):
    """
    Represent a rail.
    """

    @abc.abstractmethod
    def add_mark(self, mark: utils.geometry.IImagePoint) -> None:
        """
        Add a mark to the rail.
        :param mark: Mark to add.
        """
        pass

    @abc.abstractmethod
    def get_nearest_mark(self, position: utils.geometry.IImagePoint) -> [int, float]:
        """
        index and distance to mark closest to position
        :param position: position to which the mark should be closest.
        """
        pass

    @abc.abstractmethod
    def del_mark(
        self,
        mark: Optional[utils.geometry.IImagePoint] = None,
        mark_index: Optional[int] = None,
    ) -> Optional[int]:
        """
        Delete either mark near to given marking point or delete mark by index.
        Both parameters are ambiguous and therefore forbidden.
        :param mark: Rough mark to delete
        :param mark_index: Index of sorted mark list
        :return: Index of deleted item
        """
        pass

    @property
    @abc.abstractmethod
    def marks(self) -> list[utils.geometry.IImagePoint]:
        pass

    @property
    @abc.abstractmethod
    def world_width(self) -> float:
        pass

    @abc.abstractmethod
    def spline_points(self, steps: int) -> list[utils.geometry.IImagePoint]:
        """
        Calculate interpolated points for marks.
        :param steps: Interpolation steps
        :return: Interpolated rail points
        """
        pass

    @abc.abstractmethod
    def mark_points_image_widths(self, camera: utils.camera.ICamera) -> list[int]:
        """
        Calculate list of width between facing mark contour points.
        :param camera: Image to world calculator
        :return: List of width for each mark in px
        """
        pass

    @abc.abstractmethod
    def spline_points_image_widths(
        self, camera: utils.camera.ICamera, steps: int
    ) -> list[int]:
        """
        Calculate list of width between facing spline contour points.
        :param camera: Image to world calculator
        :param steps: Interpolation steps
        :return: Widths of rail
        """
        pass

    @abc.abstractmethod
    def contour_points_splines_left(
        self, camera: utils.camera.ICamera, steps: int
    ) -> list[utils.geometry.IImagePoint]:
        """
        Calculating points describing contour bordering left side of the rail.
        :param camera: Image to world calculator
        :param steps: Interpolation steps
        :return: Points describing rail contour
        """
        pass

    @abc.abstractmethod
    def contour_points_splines_right(
        self, camera: utils.camera.ICamera, steps: int
    ) -> list[utils.geometry.IImagePoint]:
        """
        Calculating points describing contour bordering right side of the rail.
        :param camera: Image to world calculator
        :param steps: Interpolation steps
        :return: Points describing rail contour
        """
        pass

    @abc.abstractmethod
    def contour_points_splines(
        self,
        camera: utils.camera.ICamera,
        steps: int,
    ) -> list[utils.geometry.IImagePoint]:
        """
        Calculating points describing contour bordering the rail.
        The points describe the contour of the rail clockwise starting
        from the bottom left.
        :param camera: Image to world calculator
        :param steps: Interpolation steps
        :return: Points describing rail contour
        """
        pass


class Rail(IRail):
    """
    Represent a rail.
    """

    def __init__(
        self,
        width: float,
        marks: Optional[list[utils.geometry.IImagePoint]] = None,
    ) -> None:
        """
        :param width: Rail width in mm
        :param marks: Marks on rail
        """
        marks = [] if not marks else marks
        self._world_width: float = width
        self._marks: list[utils.geometry.IImagePoint] = marks

    def add_mark(self, mark: utils.geometry.IImagePoint) -> None:
        """
        Add a mark to the rail.
        :param mark: Mark to add.
        """
        if not mark in self._marks:
            self._marks.append(mark)
            self._marks = sorted(self._marks)

    def get_nearest_mark(self, position: utils.geometry.IImagePoint) -> [int, float]:
        """
        index and distance to mark closest to position
        :param position: position to which the mark should be closest.
        """
        cutoff = 5
        nearest_dist = cutoff
        nearest_index = -1
        for mark, index in zip(self._marks, range(len(self._marks))):
            dist = math.dist(position.point, mark.point)

            if dist <= nearest_dist:
                nearest_dist = dist
                nearest_index = index

        return nearest_index, nearest_dist

    def del_mark(
        self,
        mark: Optional[utils.geometry.IImagePoint] = None,
        mark_index: Optional[int] = None,
    ) -> Optional[int]:
        """
        Delete either mark near to given marking point or delete mark by index.
        Both parameters are ambiguous and therefore forbidden.
        :param mark: Rough mark to delete
        :param mark_index: Index of sorted mark list
        :return: Index of deleted item
        """
        if mark is None and mark_index is None:
            msg: str = "Expected ether mark near to delete or index of mark, got none."
            raise ValueError(msg)
        if mark is not None and mark_index is not None:
            msg = "Expected ether mark near to delete or index of mark, got both. "
            msg += "This is ambiguous."
            raise ValueError(msg)
        # Can only delete point if there is at least one
        if len(self._marks) >= 1:
            # Delete py approximate distance
            if mark is not None:
                mark_points_arr: np.ndarray
                mark_points_arr = np.vstack([mark.point for mark in self._marks])
                # Calculate euclidean distance for all points
                distances: np.ndarray = np.linalg.norm(
                    mark_points_arr - mark.point, axis=1
                )
                # Get index for item with the shortest distance
                index: int = np.argmin(distances).item()
            # Delete by list index
            elif mark_index is not None:
                index = mark_index
            self._marks.pop(index)
            return index

    @property
    def marks(self) -> list[utils.geometry.IImagePoint]:
        return self._marks

    @property
    def world_width(self) -> float:
        return self._world_width

    def spline_points(self, steps: int) -> list[utils.geometry.IImagePoint]:
        """
        Calculate interpolated points for marks.
        :param steps: Interpolation steps
        :return: Interpolated rail points
        """
        spline_points: list[utils.geometry.IImagePoint]
        spline_points = utils.geometry.calculate_splines(tuple(self._marks), steps)
        
        # variante mit nur einem Punkt pro Bildzeile:
        if len(spline_points) > 0:
            i = 1
            last_y  = spline_points[-1].y
            first_y = spline_points[0].y
            while i < len(spline_points)-1:
                y = spline_points[i].y
                if y != last_y and y != first_y:
                    indices = [j for j, p in enumerate(spline_points) if p.y == y]
                    if len(indices) > 1:
                        li = i+int(len(indices)/2)
                        spline_points = [p for j, p in enumerate(spline_points) if (p.y != y or j == li)]
            
                elif y == last_y and y != first_y:
                    spline_points = [p for j, p in enumerate(spline_points) if p.y != y or j == len(spline_points)-1]
                elif y != last_y and y == first_y:
                    spline_points = [p for j, p in enumerate(spline_points) if p.y != y or j == 0]
                
                i = i+1

        #Variante Glättung nur Ecken entfernen:
        #if len(spline_points) > 0:
        #    new_spline_points = [p for j, p in enumerate(spline_points) if j == 0 or j == len(spline_points)-1 or (p.y != spline_points[j+1].y or p.x != spline_points[j-1].x)]


        return spline_points

    def mark_points_image_widths(self, camera: utils.camera.ICamera) -> list[np.int_]:
        """
        Calculate list of width between facing mark contour points.
        :param camera: Image to world calculator
        :return: List of width for each mark in px
        """
        left_points: list[utils.geometry.IImagePoint]
        left_points = self._contour_points_marks_left(camera)
        right_points: list[utils.geometry.IImagePoint]
        right_points = self._contour_points_marks_right(camera)
        return self._points_image_widths(left_points, right_points)

    def spline_points_image_widths(
        self,
        camera: utils.camera.ICamera,
        steps: int,
    ) -> list[np.int_]:
        """
        Calculate list of width between facing spline contour points.
        :param camera: Image to world calculator
        :param steps: Interpolation steps
        :return: Widths of rail
        """
        left_points: list[utils.geometry.IImagePoint]
        left_points = self.contour_points_splines_left(camera, steps)
        right_points: list[utils.geometry.IImagePoint]
        right_points = self.contour_points_splines_right(camera, steps)
        return self._points_image_widths(left_points, right_points)

    @staticmethod
    def _points_image_widths(
        left_points: list[utils.geometry.IImagePoint],
        right_points: list[utils.geometry.IImagePoint],
    ) -> list[np.int_]:
        """
        Calculate list of width between facing points on rail contour.
        :param left_points: Points on left contour
        :param right_points: Point on right contour
        :return: List of width in px
        """
        widths: list[np.int_] = []
        for left_point, right_point in zip(left_points, right_points):
            widths.append(max(1, right_point.x - left_point.x))
        return widths

    def contour_points_splines_left(
        self,
        camera: utils.camera.ICamera,
        steps: int,
    ) -> list[utils.geometry.IImagePoint]:
        """
        Calculating points describing contour bordering left side of the rail.
        :param camera: Image to world calculator
        :param steps: Interpolation steps
        :return: Points describing rail contour
        """
        points: list[utils.geometry.IImagePoint] = self.spline_points(steps)
        return self._contour_points_side(points, camera, RailSide.LEFT)

    def contour_points_splines_right(
        self,
        camera: utils.camera.ICamera,
        steps: int,
    ) -> list[utils.geometry.IImagePoint]:
        """
        Calculating points describing contour bordering right side of the rail.
        :param camera: Image to world calculator
        :param steps: Interpolation steps
        :return: Points describing rail contour
        """
        points: list[utils.geometry.IImagePoint] = self.spline_points(steps)
        return self._contour_points_side(points, camera, RailSide.RIGHT)

    def _contour_points_marks_left(
        self,
        camera: utils.camera.ICamera,
    ) -> list[utils.geometry.IImagePoint]:
        """
        Calculate mark points describing contour bordering left side of the rail.
        :param camera: Image to world calculator
        :return: Points describing rail contour
        """
        return self._contour_points_side(self.marks, camera, RailSide.LEFT)

    def _contour_points_marks_right(
        self,
        camera: utils.camera.ICamera,
    ) -> list[utils.geometry.IImagePoint]:
        """
        Calculate mark points describing contour bordering right side of the rail.
        :param camera: Image to world calculator
        :return: Points describing rail contour
        """
        return self._contour_points_side(self.marks, camera, RailSide.RIGHT)

    def contour_points_splines(
        self,
        camera: utils.camera.ICamera,
        steps: int,
    ) -> list[utils.geometry.IImagePoint]:
        """
        Calculating points describing contour bordering the rail.
        The points describe the contour of the rail clockwise starting
        from the bottom left.
        :param camera: Image to world calculator
        :param steps: Interpolation steps
        :return: Points describing rail contour
        """
        contour_left: list[utils.geometry.IImagePoint]
        contour_left = self.contour_points_splines_left(camera, steps)
        # Reverse to get clockwise point pattern
        contour_right: list[utils.geometry.IImagePoint]
        contour_right = self.contour_points_splines_right(camera, steps)[::-1]
        return [*contour_left, *contour_right]

    def _contour_points_side(
        self,
        points: list[utils.geometry.IImagePoint],
        camera: utils.camera.ICamera,
        side: RailSide,
    ) -> list[utils.geometry.IImagePoint]:
        """
        Calculate points describing contour bordering given side of the rail.
        :param camera: Image to world calculator
        :param side: Side of the rail
        :return: Points describing rail contour
        """
        contour_points_side: list[utils.geometry.IImagePoint] = []
        if len(points) > 0:
            # Add or subtract half rail width
            world_width: float = (self.world_width / 2) * side
            for point in points:
                contour_point: utils.geometry.IImagePoint
                contour_point = camera.point_from_distance(point, world_width, "x")
                contour_point = utils.geometry.ImagePoint(contour_point.x, point.y)
                contour_points_side.append(contour_point)
        return contour_points_side
