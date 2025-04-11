from typing import Union
import abc
from . import rail
from .track import ITrack, Track, TrackPosition


class ITrackSerializer(metaclass=abc.ABCMeta):
    """
    Turn track object in a serial format and vice versa.
    """

    @staticmethod
    @abc.abstractmethod
    def serialize(track: ITrack) -> dict:
        """
        Track object implementing ITrack interface.
        :return: Dictionary describing ITrack object.
        """
        pass

    @staticmethod
    @abc.abstractmethod
    def de_serialize(track_dict: dict, track_id: int) -> ITrack:
        """
        Create Track object from serial description of a track.
        :return: Track object with attributes from stream.
        """
        pass


TrackDict = dict[str, Union[int, rail.RailDict, str]]


class DictTrackSerializer(ITrackSerializer):
    """
    Turn track object in a dict object and vice versa.
    """

    def __init__(self):
        self.rail_serializer = rail.DictRailSerializer()

    def serialize(self, track: ITrack) -> TrackDict:
        """
        Turn object implementing ITrack interface into dict.
        :return: Dictionary describing ITrack object.
        """
        track_dict: TrackDict
        track_dict = {
            "relative position": track.position,
            "left rail": self.rail_serializer.serialize(track.left_rail),
            "right rail": self.rail_serializer.serialize(track.right_rail),
        }
        return track_dict

    def de_serialize(self, track_dict: TrackDict, track_id: int) -> ITrack:
        """
        Turn dict into Track object.
        :return: Track object
        """
        track_id: int = track_id
        left_rail: rail.IRail
        left_rail = self.rail_serializer.de_serialize(track_dict["left rail"])
        right_rail: rail.IRail
        right_rail = self.rail_serializer.de_serialize(track_dict["right rail"])
        position: TrackPosition = TrackPosition(track_dict["relative position"])
        return Track(track_id, position, left_rail, right_rail)
