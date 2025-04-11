import abc
from labels4rails import utils
from .rail import IRail, Rail


class IRailSerializer(metaclass=abc.ABCMeta):
    """
    Turn rail object in a serial format and vice versa.
    """

    @staticmethod
    @abc.abstractmethod
    def serialize(rail: IRail) -> dict:
        """
        Serialize object implementing IRail interface.
        :return: Dictionary describing IRail object.
        """
        pass

    @staticmethod
    @abc.abstractmethod
    def de_serialize(rail_dict: dict, rail_width: float) -> IRail:
        """
        Create Rail object from serial description of a rail.
        :return: Rail object with attributes from stream.
        """
        pass


RailDict = dict[str, list[dict[str, int]]]


class DictRailSerializer(IRailSerializer):
    """
    Turn Rail object in a dict object and vice versa.
    """

    @staticmethod
    def serialize(rail: IRail) -> RailDict:
        """
        Turn object implementing IRail interface into dict.
        :return: Dictionary describing IRail object.
        """
        mark: utils.geometry.IImagePoint
        rail_dict: RailDict
        rail_dict = {
            "points": [{"x": mark.x.item(), "y": mark.y.item()} for mark in rail.marks]
        }
        return rail_dict

    @staticmethod
    def de_serialize(rail_dict: dict, rail_width: int = 67) -> IRail:
        """
        Turn dict into Rail object.
        :return: Rail object
        """
        rail_points: list[utils.geometry.IImagePoint] = []
        point: dict[str, int]
        for point in rail_dict["points"]:
            x: int = point["x"]
            y: int = point["y"]
            rail_points.append(utils.geometry.ImagePoint(x, y))
        return Rail(rail_width, rail_points)
