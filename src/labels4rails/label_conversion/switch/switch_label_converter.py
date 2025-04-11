from typing import Iterable, Optional
import abc
import dataclasses
import itertools
import pathlib
from labels4rails import data
from labels4rails import scene
from labels4rails.utils import config

from ..TagFilter import TagFilter


@dataclasses.dataclass(frozen=True)
class SwitchYoloLabel:
    """
    Represent switch attributes and bounding box in YOLO format relative to
    image resolution.
    """

    kind: scene.target.SwitchKind
    direction: scene.target.SwitchDirection
    width: float
    height: float
    center_x: float
    center_y: float


class ISwitchLabelConverter(metaclass=abc.ABCMeta):
    """
    Generate labels for switches.
    """

    @abc.abstractmethod
    def __init__(
        self,
        dataset: data.IDataSet,
    ) -> None:
        """
        :param dataset: RailLabel dataset
        """
        pass

    @abc.abstractmethod
    def __call__(
        self,
        output_path: pathlib.Path,
        kinds: Optional[list[scene.target.SwitchKind]] = None,
        directions: Optional[list[scene.target.SwitchDirection]] = None,
    ) -> None:
        """
        Store switch labels  in given path. Class ids are generated from all 
        combinations between given switch kinds and switch directions. If 
        either 'kind' or 'direction' is empty this attribute is considered as 
        not interesting. Being both empty is invalid. That means if the switch 
        is selected by the other attribute class ids get grouped. E.g. if 
        directions list ist empty and merges are selected in the kinds list 
        all merges will get the same class id.
        :param output_path: Path to store labels
        :param kinds: List of desired switch kinds
        :param directions: List of desired switch directions
        """
        pass


class SwitchLabelConverterYOLO(ISwitchLabelConverter):
    """
    Generate YOLO labels for switches.
    """

    def __init__(
        self,
        dataset: data.IDataSet,
        cfg: config.Labels4RailsConfig,
    ) -> None:
        """
        :param dataset: RailLabel dataset
        """
        self._dataset: data.IDataSet = dataset
        self._scene_deserializer: scene.ISceneSerializer
        self._scene_deserializer = scene.DictSceneSerializer()
        self._cfg = cfg

    def __call__(
        self,
        output_path: pathlib.Path,
        kinds: Optional[tuple[scene.target.SwitchKind]] = None,
        directions: Optional[tuple[scene.target.SwitchDirection]] = None,
    ) -> None:
        """
        Store yolo-format labels and list of name id translation (label.txt) in
        given path. Class ids are generated from all combinations between given
        switch kinds and switch directions. If either 'kind' or 'direction' is
        empty this attribute is considered as not interesting. Being both empty
        is invalid. That means if the switch is selected by the other attribute
        class ids get grouped. E.g. if directions list ist empty and merges are
        selected in the kinds list all merges will get the same class id.
        :param output_path: Path to store labels
        :param kinds: List of desired switch kinds
        :param directions: List of desired switch directions
        """
        if kinds is None and directions is None:
            msg: str = "Expected at least one switch attribute (kind or direction), "
            msg += "got neither."
            raise ValueError(msg)
        kinds = () if kinds is None else kinds
        directions = () if directions is None else directions

        combos: tuple[tuple[scene.target.SwitchKind, scene.target.SwitchDirection]]
        combos = self.__calculate_combinations(kinds, directions)

        data_: data.Data
        filtered_list = TagFilter(self._dataset._annotations_path, self._cfg).annotationList
        for data_ in self._dataset:
            if data_.name in filtered_list:
                switches, resolution = self.__prepare_switches(data_)
                yolo_switches: list[SwitchYoloLabel]
                yolo_switches = self.__calculate_box_labels(resolution, switches)
                selected_switches: list[SwitchYoloLabel]
                selected_switches = self.__filter_switches(yolo_switches, kinds, directions)
                switches_with_id: dict[SwitchYoloLabel, int]
                switches_with_id = self.__calculate_class_ids(selected_switches, combos)
                self.__save_box_label(switches_with_id, output_path, data_.name)

        self.__save_class_id_text(combos, output_path)

    def __prepare_switches(
        self,
        data_: data.Data,
    ) -> tuple[Iterable[scene.target.ISwitch], tuple[int, int]]:
        """
        Read switches and image resolution from RailLabel dataset.
        :param data_: Item of RailLabel dataset
        :return: Switches on scene, scene image resolution
        """
        scene_: scene.IScene
        scene_ = self._scene_deserializer.de_serialize(data_.annotation)
        resolution: tuple[int, int] = data_.image.shape[:2]
        switches: Iterable[scene.target.ISwitch] = scene_.switches.values()
        return switches, resolution

    @staticmethod
    def __calculate_combinations(
        kinds,
        directions,
    ) -> tuple[tuple[scene.target.SwitchKind, scene.target.SwitchDirection]]:
        """
        Calculate combination between given list of switch kinds and given list
        of switch directions.
        :param kinds: Switch kind attributes
        :param directions: Switch direction attributes
        :return: Combination of kinds and attributes
        """
        kinds = ((),) if kinds is None or len(kinds) == 0 else kinds
        directions = ((),) if directions is None or len(directions) == 0 else directions
        combinations: tuple[
            tuple[scene.target.SwitchKind, scene.target.SwitchDirection]
        ]
        combinations = tuple(itertools.product(kinds, directions))
        return combinations

    @staticmethod
    def __filter_switches(
        switches: list[SwitchYoloLabel],
        kinds: Optional[tuple[scene.target.SwitchKind]] = None,
        directions: Optional[tuple[scene.target.SwitchDirection]] = None,
    ) -> list[SwitchYoloLabel]:
        """
        Filter list to only contain switches to contain only switches with
        attributes given list of kinds and directions.
        :param switches: Switches in yolo format
        :param kinds: List of desired switch kinds
        :param directions: List of desired switch directions
        :return: Filtered yolo-format switches with corresponding id
        """
        kinds = tuple() if kinds is None else kinds
        directions = tuple() if directions is None else directions

        selected_switches: list[SwitchYoloLabel] = []
        switch: SwitchYoloLabel
        for switch in switches:
            if switch.kind in kinds or switch.direction in directions:
                selected_switches.append(switch)
        return selected_switches

    @staticmethod
    def __calculate_class_ids(
        switches: list[SwitchYoloLabel],
        combinations,
    ) -> dict[SwitchYoloLabel, int]:
        """
        Calculate label class id for given combination of switch attributes.
        :return: Yolo switches with corresponding class id
        """
        id_dict: dict[SwitchYoloLabel, int] = {}
        combo: list[tuple[scene.target.SwitchKind, scene.target.SwitchDirection]]
        for id_, combo in enumerate(combinations):
            kind: scene.target.SwitchKind
            direction: scene.target.SwitchDirection
            kind, direction = combo
            switch: SwitchYoloLabel
            for switch in switches:
                # There is no kind attribute
                if kind == ():
                    if switch.direction == direction:
                        id_dict[switch] = id_
                # There is no direction attribute
                elif direction == ():
                    if switch.kind == kind:
                        id_dict[switch] = id_
                # There is  at leas one kind and at leas one direction attribute
                else:
                    if switch.kind == kind and switch.direction == direction:
                        id_dict[switch] = id_
        return id_dict

    @staticmethod
    def __calculate_box_labels(
        resolution: tuple[int, int],
        switches: Iterable[scene.target.ISwitch],
    ) -> list[SwitchYoloLabel]:
        """
        Calculate relative yolo-coordinates from absolute RailLabel scene
        coordinates.
        :param resolution: Resolution of the scene image
        :param switches: Switches on the scene
        :return: Switches in relative yolo format
        """
        yolo_switches: list[SwitchYoloLabel] = []
        for switch in switches:
            if len(switch.marks) == 2:
                center = switch.marks[0].midpoint(switch.marks[1])
                center_x = center.x / resolution[1]
                center_y = center.y / resolution[0]
                width = abs(switch.marks[0].x - switch.marks[1].x) / resolution[1]
                height = abs(switch.marks[0].y - switch.marks[1].y) / resolution[0]

                label: SwitchYoloLabel
                label = SwitchYoloLabel(
                    switch.kind,
                    switch.direction,
                    width,
                    height,
                    center_x,
                    center_y,
                )
                yolo_switches.append(label)
        return yolo_switches

    @staticmethod
    def __save_box_label(
        yolo_switches: dict[SwitchYoloLabel, id],
        output_path: pathlib.Path,
        file_stem: str,
    ) -> None:
        """
        Write scene in yolo format to given path. Yolo labels get the same name
        as the scene and have a '.txt' suffix.
        :param yolo_switches: Yolo format switches with corresponding label id
        :param output_path: Path to save labels
        :param file_stem: Stem name of the RailLabel scene
        """
        output_path = output_path / (file_stem + ".txt")
        with open(output_path, "w") as file:
            for switch_attributes, switch_id in yolo_switches.items():
                label = f"{switch_id} {switch_attributes.center_x} "
                label += f"{switch_attributes.center_y} {switch_attributes.width} "
                label += f"{switch_attributes.height}\n"
                file.write(label)

    @staticmethod
    def __save_class_id_text(
        combinations: tuple[
            tuple[scene.target.SwitchKind, scene.target.SwitchDirection]
        ],
        output_path: pathlib.Path,
    ) -> None:
        """
        Save the file for translating label class ids and label names
        'labels.txt' in given path.
        :param combinations: Combination of desired switch kinds and directions
        :param output_path: Path to store label class name file
        """
        output_path = output_path / "labels.txt"
        with open(output_path, "w") as file:
            for combo in combinations:
                kind: str
                if combo[0] == ():
                    kind = "N.a."
                else:
                    kind = combo[0].value
                direction: str
                if combo[1] == ():
                    direction = "N.a."
                else:
                    direction = combo[1].value
                file.write(f"kind:_{kind},_direction:_{direction}\n")
