from typing import Optional, Union
import abc
import enum
from labels4rails import utils
import numpy as np
import numpy.typing as npt


class SwitchDirection(enum.Enum):
    """
    Possible directions of a switch
    """

    RIGHT: str = "right"
    LEFT: str = "left"
    UNKNOWN: str = "unknown"


class SwitchKind(enum.Enum):
    """
    Possible kinds of switches.
    """

    FORK: str = "fork"
    MERGE: str = "merge"
    UNKNOWN: str = "unknown"


SwitchAttributeCombo = tuple[SwitchKind, SwitchDirection]


class ISwitch:
    """
    Represent a switch.
    """

    @abc.abstractmethod
    def __init__(
        self,
        switch_id: int,
        kind: SwitchKind,
        direction: SwitchDirection,
        marks: list[utils.geometry.IImagePoint, utils.geometry.IImagePoint] = None,
        track_ids: list[int] = None,
    ) -> None:
        """
        :param switch_id: Unique ID on scene
        :param kind: Kind of switch
        :param direction: Direction of switch
        :param marks: List of marks describing bounding box
        :param track_ids: Unique IDs of tracks connected by switch
        """
        pass

    @abc.abstractmethod
    def add_mark(self, marks: list[utils.geometry.IImagePoint]):
        """
        Add mark to describe bounding box.
        :param marks: List containing one mark.
        """
        pass

    @abc.abstractmethod
    def del_mark(self, marks: list[utils.geometry.IImagePoint]):
        """
        Delete the nearest mark to given mark.
        :param marks: List containing one rough mark to remove
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
    def marks(self) -> list[utils.geometry.IImagePoint]:
        pass

    @property
    @abc.abstractmethod
    def kind(self) -> SwitchKind:
        pass

    @property
    @abc.abstractmethod
    def direction(self) -> SwitchDirection:
        pass

    @property
    @abc.abstractmethod
    def track_ids(self) -> list[int]:
        pass

    @property
    def selected(self):
        pass

    @selected.setter
    def selected(self, value):
        pass

    @kind.setter
    @abc.abstractmethod
    def kind(self, value):
        pass

    @direction.setter
    @abc.abstractmethod
    def direction(self, value):
        pass


class Switch(ISwitch):
    """
    Represent a witch.
    """

    def __init__(
        self,
        switch_id: int,
        kind: SwitchKind,
        direction: SwitchDirection,
        marks: list[utils.geometry.IImagePoint, utils.geometry.IImagePoint] = None,
        track_ids: list[int] = None,
    ) -> None:
        """
        :param switch_id: Unique ID on scene
        :param kind: Kind of switch
        :param direction: Direction of switch
        :param marks: List of marks describing bounding box
        :param track_ids: Unique IDs of tracks connected by switch
        """
        self._id = switch_id
        self._kind: Optional[SwitchKind] = kind
        self._direction: Optional[SwitchDirection] = direction
        self._track_ids: list[int] = [] if track_ids is None else track_ids
        self._marks: list[utils.geometry.IImagePoint, utils.geometry.IImagePoint]
        self._marks = [] if marks is None else marks
        self._selected = False

    def add_mark(self, marks: list[utils.geometry.IImagePoint]):
        """
        Add mark to describe bounding box.
        :param marks: List containing one mark.
        """
        if len(self.marks) < 2:
            self.marks.append(marks[0])

    def del_mark(self, marks: list[utils.geometry.IImagePoint]):
        """
        Delete the nearest mark to given mark.
        :param marks: List containing one rough mark to remove
        """
        # Can only delete point if there is at least one
        if len(self._marks) >= 1:
            mark_points_arr: npt.NDArray[np.int_]
            mark_points_arr = np.vstack([mark.point for mark in self._marks])
            # Calculate euclidean distance for all points
            distances: np.ndarray
            distances = np.linalg.norm(mark_points_arr - marks[0].point, axis=1)
            lowest_dist_index: int = np.argmin(distances).item()
            self._marks.pop(lowest_dist_index)

    def add_track_ids(self, track_ids: list[int]):
        """
        Add track IDs to switch.
        :param track_ids: List of track IDs
        """
        self._track_ids.extend(track_ids)

    def del_track_ids(self, track_ids: list[int]):
        """
        Delete track IDs from switch.
        :param track_ids: List of track IDs
        """
        self._track_ids = [track_id for track_id in self._track_ids if track_id not in track_ids]

    def __str__(self) -> str:
        return f"{self._id:02d}, {self._kind.value}, {self._direction.value}"

    @property
    def id(self) -> int:
        return self._id

    @property
    def marks(self) -> list[utils.geometry.IImagePoint]:
        return self._marks

    @property
    def kind(self) -> SwitchKind:
        return self._kind

    @kind.setter
    def kind(self, value):
        self._kind = value

    @property
    def direction(self) -> SwitchDirection:
        return self._direction

    @direction.setter
    def direction(self, value):
        self._direction = value

    @property
    def track_ids(self) -> list[int]:
        return self._track_ids

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        self._selected = value
