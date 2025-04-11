import abc
from . import target
from .scene import IScene, Scene

# convert scene items to json format

class ISceneSerializer(metaclass=abc.ABCMeta):
    """
    Turn scene object in a serial format and vice versa.
    """

    @abc.abstractmethod
    def serialize(self, scene: IScene) -> dict:
        """
        Serialize object implementing IScene interface.
        :return: Dictionary describing IScene object.
        """
        pass

    @abc.abstractmethod
    def de_serialize(self, track_dict: dict) -> IScene:
        """
        Create Scene object from serial description of a scene.
        :return: Scene object with attributes from stream.
        """
        pass


class DictSceneSerializer(ISceneSerializer):
    """
    Turn switch object in a dict object and vice versa.
    """

    def __init__(self):
        self.tag_group_serializer = target.DictTagGroupSerializer()
        self.track_serializer = target.DictTrackSerializer()
        self.switch_serializer = target.DictSwitchSerializer()

    def serialize(self, scene: IScene) -> dict:
        """
        Turn object implementing IScene interface into dict.
        :return: Dictionary describing IScene object.
        """
        tracks: dict[int, target.TrackDict] = {}
        for track_id, track in scene.tracks.items():
            tracks[track_id] = self.track_serializer.serialize(track)

        switches: dict[int, target.SwitchDict] = {}
        for switch_id, switch in scene.switches.items():
            switches[switch_id] = self.switch_serializer.serialize(switch)

        tag_groups = self.tag_group_serializer.serialize(scene.tag_groups)

        scene_dict: dict
        scene_dict = {"tag groups": tag_groups, "tracks": tracks, "switches": switches}

        return scene_dict

    def de_serialize(self, scene_dict: dict) -> IScene:
        """
        Turn dict into Scene object.
        :return: Scene object
        """
        if not isinstance(scene_dict, dict):
            msg: str = f"Expected scene dict to be of type dict, got {type(scene_dict)}"
            raise ValueError(msg)

        tag_groups: target.TagGroups
        group_name: str
        if "tag groups" in scene_dict:
            tag_groups = self.tag_group_serializer.de_serialize(
                scene_dict["tag groups"]
            )
        else:
            tag_groups = target.TagGroups([], [], [], [], [], [])

        tracks: dict[int, target.ITrack] = {}
        track_id: str
        track: dict
        for track_id, track in scene_dict["tracks"].items():
            track_id_int: int = int(track_id)
            tracks[track_id_int] = self.track_serializer.de_serialize(
                track, track_id_int
            )

        switches: dict[int, target.ISwitch] = {}
        switch_id: str
        if "switches" in scene_dict:
            for switch_id, switch in scene_dict["switches"].items():
                switch_id_int: int = int(switch_id)
                switches[switch_id_int] = self.switch_serializer.de_serialize(
                    switch, switch_id_int
                )

        scene: IScene = Scene(tag_groups, tracks, switches)

        return scene
