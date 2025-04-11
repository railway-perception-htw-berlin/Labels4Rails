from typing import Optional
import abc
import dataclasses
from .tags import TagGroups

TagGroupDict = dict[str, dict[str, bool]]


class ITagGroupSerializer(metaclass=abc.ABCMeta):
    """
    Turn tag object in a serial format and vice versa.
    """

    @abc.abstractmethod
    def serialize(self, tag_groups: TagGroups) -> TagGroupDict:
        """
        Serialize object implementing ITag interface.
        :return: Dictionary describing ITag object.
        """
        pass

    @abc.abstractmethod
    def de_serialize(self, tag_dict: Optional[TagGroupDict]) -> TagGroups:
        """
        Create Tag object from serial description of a tags.
        :return: Tags object with attributes from stream.
        """
        pass


class DictTagGroupSerializer(ITagGroupSerializer):
    """
    Turn switch object in a dict object and vice versa.
    """

    def serialize(self, tag_groups: TagGroups) -> TagGroupDict:
        """
        Turn object implementing ITag interface into dict.
        :return: Dictionary describing ITag object.
        """
        return dataclasses.asdict(tag_groups)

    def de_serialize(self, tag_dict: Optional[TagGroupDict]) -> TagGroups:
        """
        Turn dict into Tag object.
        :return: Tag object
        """
        tag_groups: TagGroups
        if tag_dict is None:
            tag_groups = TagGroups([], [], [], [], [], [])
        else:
            tag_groups = TagGroups(
                tag_dict["track_layout"] if "track_layout" in tag_dict else [],
                tag_dict["weather"] if "weather" in tag_dict else [],
                tag_dict["light"] if "light" in tag_dict else [],
                tag_dict["time_of_day"] if "time_of_day" in tag_dict else [],
                tag_dict["environment"] if "environment" in tag_dict else [],
                tag_dict["additional_attributes"]
                if "additional_attributes" in tag_dict
                else [],
            )
        return tag_groups
