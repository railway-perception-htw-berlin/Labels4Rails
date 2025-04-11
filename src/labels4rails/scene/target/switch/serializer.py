from typing import Union, Optional
import abc
from labels4rails import utils
from .switch import ISwitch, Switch, SwitchKind, SwitchDirection
import numpy as np


SwitchDict = dict[str, Union[list[dict[str, int], dict[str, int]], str, str, int]]


class ISwitchSerializer(metaclass=abc.ABCMeta):
    """
    Turn switch object in a serial format and vice versa.
    """

    @staticmethod
    @abc.abstractmethod
    def serialize(switch: ISwitch) -> dict:
        """
        Serialize object implementing ISwitch interface.
        :return: Dictionary describing ISwitch object.
        """
        pass

    @staticmethod
    @abc.abstractmethod
    def de_serialize(track_dict: dict, switch_id: int) -> ISwitch:
        """
        Create Switch object from serial description of a switch.
        :return: Switch object with attributes from stream.
        """
        pass


class DictSwitchSerializer(ISwitchSerializer):
    """
    Turn switch object in a dict object and vice versa.
    """

    @staticmethod
    def serialize(switch: ISwitch) -> SwitchDict:
        """
        Turn object implementing ISwitch interface into dict.
        :return: Dictionary describing ISwitch object.
        """
        switch_dict: SwitchDict
        switch_dict = {
            "marks": [
                {"x": mark.x.item(), "y": mark.y.item()} for mark in switch.marks
            ],
            "kind": switch.kind.value,
            "direction": switch.direction.value,
            "track_ids": [track_id for track_id in switch.track_ids],
        }
        return switch_dict

    @staticmethod
    def de_serialize(switch_dict: SwitchDict, switch_id: int) -> ISwitch:
        """
        Turn dict into Switch object.
        :return: Switch object
        """
        if switch_dict["marks"]:
            x: int = switch_dict["marks"][0]["x"]
            y: int = switch_dict["marks"][0]["y"]
            mark_1: utils.geometry.IImagePoint
            mark_1 = utils.geometry.ImagePoint(x, y)
            x = switch_dict["marks"][1]["x"]
            y = switch_dict["marks"][1]["y"]
            mark_2: utils.geometry.IImagePoint
            mark_2 = utils.geometry.ImagePoint(x, y)
            marks: Optional[
                list[utils.geometry.IImagePoint, utils.geometry.IImagePoint]
            ]
            marks = [mark_1, mark_2]
        else:
            marks = None
        kind: SwitchKind = SwitchKind(switch_dict["kind"])
        direction: SwitchDirection = SwitchDirection(switch_dict["direction"])
        tracks: list[int]
        tracks = switch_dict["track_ids"] if "track_ids" in switch_dict else None
        return Switch(switch_id, kind, direction, marks, tracks)
