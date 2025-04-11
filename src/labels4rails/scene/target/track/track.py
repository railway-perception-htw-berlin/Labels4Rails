from typing import Optional
import abc
from labels4rails import utils
from . import rail
import enum


class TrackPosition(str, enum.Enum):
    """
    Possible track positions
    """

    LEFT = "left"
    RIGHT = "right"
    EGO = "ego"



class ITrack(metaclass=abc.ABCMeta):
    """
    Represent a track.
    """

    @abc.abstractmethod
    def __init__(
        self,
        track_id,
        position: str,
        left_rail: Optional[utils.geometry.IImagePoint] = None,
        right_rail: Optional[utils.geometry.IImagePoint] = None,
        rail_width: Optional[float] = None,
    ) -> None:
        """
        :param track_id: Unique ID on scene
        :param position: Relative position
        :param left_rail: Rail object
        :param right_rail: Rail object
        :param rail_width: Width of rail in mm
        """
        pass

    @abc.abstractmethod
    def __str__(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def id(self) -> int:
        pass



    @property
    @abc.abstractmethod
    def position(self) -> str:
        pass

    @position.setter
    @abc.abstractmethod
    def position(self, value):
        pass

    @property
    @abc.abstractmethod
    def right_rail(self) -> rail.IRail:
        pass

    @property
    @abc.abstractmethod
    def left_rail(self) -> rail.IRail:
        pass

    @abc.abstractmethod
    def del_mark(
        self,
        marks: list[utils.geometry.IImagePoint, utils.geometry.IImagePoint],
        lead_index: int,
    ) -> None:
        """
        Delete the nearest mark to given mark. From the lead point the nearest
        point is calculated. The point one the opposite rail with the same list
        index is deleted afterwards.
        :param marks: List containing two rough marks to remove
        :param lead_index: Index of point to search the nearest mark
        """
        pass

    @abc.abstractmethod
    def add_mark(
        self,
        marks: list[utils.geometry.IImagePoint, utils.geometry.IImagePoint],
    ) -> None:
        """
        Add mark to track rails.
        :param marks: List containing two marks.
        """
        pass

    @abc.abstractmethod
    def get_nearest_mark(
        self,
        mouse_position: utils.geometry.IImagePoint,
    ) -> [int, rail.RailSide]:
        """
        Get mark closest to mouse position 
        :param mouse_position: mouse position
        """
        pass


class Track(ITrack):
    """
    Represents all information of a track.
    + confirm if current Track is selected via
    :param selected: color track diffrently if selected
    """

    def __init__(
        self,
        track_id: int,
        position: TrackPosition,
        left_rail: Optional[rail.IRail] = None,
        right_rail: Optional[rail.IRail] = None,
        rail_width: Optional[float] = None,
    ) -> None:
        """
        :param track_id: Unique ID on scene
        :param position: Relative position
        :param left_rail: Rail object
        :param right_rail: Rail object
        :param rail_width: Width of rail in mm
        :param selected: Boolean if selected in Scene 
        """
        self._selected = False
        self._id: int = track_id
        self._position: str = position.value
        if left_rail is not None:
            self._left_rail = left_rail
        elif rail_width is not None:
            self._left_rail = rail.Rail(rail_width)
        else:
            raise ValueError("Expected ether rail object or rail width")

        if right_rail is not None:
            self._right_rail = right_rail
        elif rail_width is not None:
            self._right_rail = rail.Rail(rail_width)
        else:
            raise ValueError("Expected ether rail object or rail width")



    def __str__(self) -> str:
        msg: str = f"id={self._id}, position={self.position}"
        return msg

    @property
    def id(self) -> int:
        return self._id


    @property
    def position(self) -> str:
        return self._position

    @position.setter
    def position(self, value):
        self._position = value

    @property
    def right_rail(self) -> rail.IRail:
        return self._right_rail
    '''Setter and getter for selected attribute'''

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        self._selected = value

    @property
    def left_rail(self) -> rail.IRail:
        return self._left_rail

    def del_mark(
        self,
        del_point: utils.geometry.IImagePoint
    ) -> None:
        """
        Delete the nearest mark to given del_point. From the del_point the nearest
        mark is calculated.
        :param del_point: current mouse position
        """

        mark_index, railSide = self.get_nearest_mark(del_point)
        if mark_index >= 0:
            if railSide == rail.RailSide.LEFT:
                self.left_rail.del_mark(mark_index = mark_index)
            else:
                self.right_rail.del_mark(mark_index = mark_index)

    def add_mark(
        self,
        marks: list[utils.geometry.IImagePoint, utils.geometry.IImagePoint],
    ) -> None:
        """
        Add mark to track rails.
        :param marks: List containing two marks.
        """
        self.left_rail.add_mark(marks[0])
        self.right_rail.add_mark(marks[1])

    
    def get_nearest_mark(
        self,
        mouse_position: utils.geometry.IImagePoint,
    ) -> [int, rail.RailSide]:
        """
        Get mark closest to mouse position 
        :param mouse_position: mouse position
        """
        nearest_left_index, left_distance = self.left_rail.get_nearest_mark(mouse_position)
        nearest_right_index, right_distance = self.right_rail.get_nearest_mark(mouse_position)
        if nearest_left_index >= 0 and nearest_right_index >= 0:
            if right_distance < left_distance:
                return nearest_right_index, rail.RailSide.RIGHT
            else:
                return nearest_left_index, rail.RailSide.LEFT
        elif nearest_left_index >= 0:
            return nearest_left_index, rail.RailSide.LEFT
        else:
            return nearest_right_index, rail.RailSide.RIGHT
        