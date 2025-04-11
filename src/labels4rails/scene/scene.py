from typing import Optional
import abc
from . import target

# container for tracks, switches, tags

class IScene(metaclass=abc.ABCMeta):
    """
    Represent a scene.
    """

    @abc.abstractmethod
    def __init__(
        self,
        tags: Optional[target.TagGroups] = None,
        tracks: Optional[dict[int, target.ITrack]] = None,
        switches: Optional[dict[int, target.ISwitch]] = None,
    ) -> None:
        """
        :param tracks: Composed ITracks to scene
        :param switches: Composed ISwitches to scene
        :param tags: Composed ITags to scene.
        """
        pass

    @abc.abstractmethod
    def add_track(
        self, position: target.TrackPosition, rail_width: int
    ) -> target.ITrack:
        """
        Add ITrack to scene.
        :param position: Relative position of track
        :param rail_width: Width rail in mm
        :return: Track object
        """
        pass

    @abc.abstractmethod
    def del_track(self, track_id: int) -> None:
        """
        Delete ITrack from scene.
        :param track_id: Unique track ID on Scene.
        """
        pass

    @property
    @abc.abstractmethod
    def tracks(self) -> dict[int, target.ITrack]:
        pass

    @tracks.setter
    @abc.abstractmethod
    def tracks(self, tracks: dict[int, target.ITrack]) -> None:
        pass

    @abc.abstractmethod
    def add_switch(
        self,
        switch_kind: target.SwitchKind,
        switch_direction: target.SwitchDirection,
    ) -> target.ISwitch:
        """
        Add IScene object to scene.
        :param switch_kind: Kind of switch
        :param switch_direction: Direction of switch
        :return: Switch object
        """
        pass

    @abc.abstractmethod
    def del_switch(self, switch_id: int) -> None:
        """
        Delete ISwitch from scene.
        :param switch_id: Unique track ID on Scene.
        """
        pass
    @abc.abstractmethod
    def edit_switch (self, switch_id: int, switch_kind: target.SwitchKind, switch_direction: target.SwitchDirection):
        pass

    @property
    @abc.abstractmethod
    def switches(self) -> dict[int, target.ISwitch]:
        pass

    @property
    @abc.abstractmethod
    def tag_groups(self) -> target.TagGroups:
        pass

    @tag_groups.setter
    @abc.abstractmethod
    def tag_groups(self, tag_groups: target.TagGroups):
        pass


class Scene(IScene):
    """
    Represent a scene.
    """

    def __init__(
        self,
        tag_groups: Optional[target.TagGroups] = None,
        tracks: Optional[dict[int, target.ITrack]] = None,
        switches: Optional[dict[int, target.ISwitch]] = None,
    ) -> None:
        """
        :param tracks: Composed ITracks to scene
        :param switches: Composed ISwitches to scene
        :param tag_groups: Composed ITagGroup to scene.
        """
        self._tracks: dict[int, target.ITrack] = tracks if tracks else {}
        self._switches: dict[int, target.ISwitch] = switches if switches else {}
        self._tag_groups: target.TagGroups
        if tag_groups is None:
            self._tag_groups = target.TagGroups([], [], [], [], [], [])
        else:
            self._tag_groups = tag_groups

    def add_track(
        self, position: target.TrackPosition, rail_width: int
    ) -> target.ITrack:
        """
        Add ITrack to scene.
        :param position: Relative position of track
        :param rail_width: Width rail in mm
        :return: Track object
        """
        track_id: int
        if self._tracks:
            track_id = max(list(self._tracks)) + 1
        else:
            track_id = 0
        self._tracks[track_id] = target.Track(track_id, position, rail_width=rail_width)
        return self._tracks[track_id]

    def del_track(self, track_id: int) -> None:
        """
        Delete ITrack from scene.
        :param track_id: Unique track ID on Scene.
        """
        if track_id in self._tracks:
            self._tracks.pop(track_id)

    def edit_track (self, track_id: int, track_position: target.TrackPosition):
        """
        edit position of track
        :param track_id: id of track that will be edited
        :param track_position: new position of track
        """

        self._tracks[track_id].position = track_position

    @property
    def tracks(self) -> dict[int, target.ITrack]:
        return self._tracks

    @tracks.setter
    def tracks(self, tracks: dict[int, target.ITrack]) -> None:
        self._tracks = tracks

    def add_switch(
        self,
        switch_kind: target.SwitchKind,
        switch_direction: target.SwitchDirection,
    ) -> target.ISwitch:
        """
        Add IScene object to scene.
        :param switch_kind: Kind of switch
        :param switch_direction: Direction of switch
        :return: Switch object
        """
        switch_id: int
        if self._switches:
            switch_id = max(list(self._switches)) + 1
        else:
            switch_id = 0
        self._switches[switch_id] = target.Switch(
            switch_id, switch_kind, switch_direction
        )
        return self._switches[switch_id]

    def del_switch(self, switch_id: int) -> None:
        """
        Delete ISwitch from scene.
        :param switch_id: Unique track ID on Scene.
        """
        if switch_id in self._switches:
            self._switches.pop(switch_id)

    def edit_switch (self, switch_id: int, switch_kind: target.SwitchKind, switch_direction: target.SwitchDirection):
        """
        edit kind and direction of switch
        :param switch_id: switch that will be edited
        :param switch_kind: new kind of switch
        :param switch_direction: new direction of switch
        """
        self._switches[switch_id].kind = switch_kind
        self._switches[switch_id].direction = switch_direction





    @property
    def switches(self) -> dict[int, target.ISwitch]:
        return self._switches

    @property
    def tag_groups(self) -> target.TagGroups:
        return self._tag_groups

    @tag_groups.setter
    def tag_groups(self, tag_groups: target.TagGroups):
        self._tag_groups = tag_groups
