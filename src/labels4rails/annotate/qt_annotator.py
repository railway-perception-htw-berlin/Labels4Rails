import abc
import math
import enum
import pathlib
import numpy as np
import numpy.typing as npt

from typing import Optional, Union

from labels4rails import scene
from labels4rails import data
from labels4rails import gui
from labels4rails import utils
from labels4rails.utils import config
from labels4rails.scene import target
from labels4rails.gui.aiming_devices.cross_hair.draw import QtCrossHairDrawer
from labels4rails.gui.aiming_devices.track_stencil.track_stencil_drawer import QtTrackStencilDrawer


class Annotator(metaclass=abc.ABCMeta):
    """
    Annotate a railroad vide image scene with marks.
    """

    @abc.abstractmethod
    def __init__(self, cfg: config.Labels4RailsConfig) -> None:
        """
        :param cfg: Configuration data class
        """
        pass

    @abc.abstractmethod
    def __call__(self) -> None:
        pass


class AnnotationStrategies(enum.Enum):
    """
    Possible strategies to annotate objects on a scene.
    """

    TRACK = 0
    SWITCH = enum.auto()


class AnnotationStrategy(metaclass=abc.ABCMeta):
    """
    Annotation strategy to annotate objects on a scene.
    """

    @abc.abstractmethod
    def __call__(
            self,
            image: npt.NDArray[np.uint8],
            position: utils.geometry.IImagePoint,
    ) -> scene.IScene:
        """
        :param image: Image to draw on
        :param position: Point of mouse
        :return: Scene with manipulated annotations
        """
        pass


class QtAnnotator(Annotator):
    def __init__(
            self, cfg: config.Labels4RailsConfig,
            dataset: data.DataSet,
            camera: utils.camera.ICamera,
            gui_event: utils.IEventHub,
            qt_scene) -> None:
        """
        modified openCVAnnotator
        """
        self._qt_scene = qt_scene
        self._dataset: data.IDataSet = dataset
        self._data_counter = 0
        self._camera: utils.camera.ICamera = camera
        self._gui_event: utils.IEventHub = gui_event
        self._strategy: Optional[AnnotationStrategies] = None
        self._strategy_handler: Optional[AnnotationStrategies]
        self._cfg: config.Labels4RailsConfig = cfg
        self._mouse: gui.IMouse
        self._mouse = gui.mouse.OpenCVMouse()
        self._scene_deserializer: scene.ISceneSerializer
        self._scene_deserializer = scene.DictSceneSerializer()
        self._image: Optional[npt.NDArray[np.uint8]] = None
        self._tag_annotator: Optional[Annotator] = None

        # Subscribe GuiEvents
        self._gui_event.subscribe(gui.GuiEvents.NEXT, self._next_scene)
        self._gui_event.subscribe(gui.GuiEvents.PREVIOUS, self._previous_scene)
        self._gui_event.subscribe(gui.GuiEvents.EXIT, self._exit_annotator)
        self._gui_event.subscribe(gui.GuiEvents.STRATEGY, self._load_strategy)
        self._gui_event.subscribe(gui.GuiEvents.TAG_COPY, self._tag_copy)
        self._gui_event.subscribe(gui.GuiEvents.TAG_COPY_OVERWRITE, self._tag_copy_overwrite)
        self._gui_event.subscribe(gui.GuiEvents.LOAD_SCENE,self._load_particular_scene)

        # Post GuiEvents
        self._gui_event.post(
            gui.GuiEvents.SCENE_COUNT, self._data_counter
        )
        self._gui_event.post(
            gui.GuiEvents.SCENE_NAME, self._dataset[self._data_counter].name
        )

        self._load_scene()
        self._load_strategy(AnnotationStrategies.TRACK)

    def __call__(self) -> None:
        pass

    def _next_scene(self) -> None:
        """
        Select next scene in dataset.
        """
        self._save_scene()
        if len(self._dataset) - 1 > self._data_counter:
            self._data_counter += 1
        else:
            self._data_counter = 0
        self._load_scene()
        self._load_strategy(self._strategy)
        self._gui_event.post(
            gui.GuiEvents.SCENE_COUNT, self._data_counter
        )
        self._gui_event.post(
            gui.GuiEvents.SCENE_NAME, self._dataset[self._data_counter].name
        )
        self._add_initial_ego_track()

    def _previous_scene(self) -> None:
        """
        Select previous scene in dataset.
        """
        self._save_scene()
        if self._data_counter > 0:
            self._data_counter -= 1
        else:
            self._data_counter = len(self._dataset) - 1
        self._load_scene()
        self._load_strategy(self._strategy)
        self._gui_event.post(
            gui.GuiEvents.SCENE_COUNT, self._data_counter
        )
        self._gui_event.post(
            gui.GuiEvents.SCENE_NAME, self._dataset[self._data_counter].name
        )
        self._add_initial_ego_track()

    def _load_particular_scene(self, name):
        self._save_scene()

        for i, image in enumerate(self._dataset._images_paths):
            if name == pathlib.Path(image).name:
                self._data_counter = i

        self._load_scene()
        self._load_strategy(self._strategy)

        self._gui_event.post(
            gui.GuiEvents.SCENE_COUNT, self._data_counter
        )
        self._gui_event.post(
            gui.GuiEvents.SCENE_NAME, self._dataset[self._data_counter].name
        )
        self._add_initial_ego_track()

    def _tag_copy(self) -> None:
        """
        Copy tag of previous image
        """
        if self._data_counter != 0:

            if not self._scene.tag_groups.additional_attributes:
                 self._scene.tag_groups.additional_attributes = list(
                     self._dataset[self._data_counter - 1].annotation["tag groups"]["additional_attributes"])
            if not self._scene.tag_groups.environment:
                self._scene.tag_groups.environment = list(
                    self._dataset[self._data_counter - 1].annotation["tag groups"]["environment"])
            if not self._scene.tag_groups.light:
                self._scene.tag_groups.light = list(
                    self._dataset[self._data_counter - 1].annotation["tag groups"]["light"])
            if not self._scene.tag_groups.time_of_day:
                self._scene.tag_groups.time_of_day = list(
                    self._dataset[self._data_counter - 1].annotation["tag groups"]["time_of_day"])
            if not self._scene.tag_groups.track_layout:
                self._scene.tag_groups.track_layout = list(
                    self._dataset[self._data_counter - 1].annotation["tag groups"]["track_layout"])
            if not self._scene.tag_groups.weather:
                self._scene.tag_groups.weather = list(
                    self._dataset[self._data_counter - 1].annotation["tag groups"]["weather"])

            # update gui
            self._gui_event.post(
                gui.GuiEvents.TAG_ALL_LISTS_UPDATE,
                {"track_layout": self._scene.tag_groups.track_layout,
                "weather": self._scene.tag_groups.weather,
                "light": self._scene.tag_groups.light,
                "time_of_day": self._scene.tag_groups.time_of_day,
                "environment": self._scene.tag_groups.environment,
                "additional": self._scene.tag_groups.additional_attributes}
            )

    def _tag_copy_overwrite(self) -> None:
        """
        Copy tag of previous image, overwrite existent tag groups
        """
        if self._data_counter != 0:
            self._scene.tag_groups.additional_attributes = list(
                self._dataset[self._data_counter - 1].annotation["tag groups"]["additional_attributes"])
            self._scene.tag_groups.environment = list(
                self._dataset[self._data_counter - 1].annotation["tag groups"]["environment"])
            self._scene.tag_groups.light = list(
                self._dataset[self._data_counter - 1].annotation["tag groups"]["light"])
            self._scene.tag_groups.time_of_day = list(
                self._dataset[self._data_counter - 1].annotation["tag groups"]["time_of_day"])
            self._scene.tag_groups.track_layout = list(
                self._dataset[self._data_counter - 1].annotation["tag groups"]["track_layout"])
            self._scene.tag_groups.weather = list(
                self._dataset[self._data_counter - 1].annotation["tag groups"]["weather"])

            # update gui
            self._gui_event.post(
                gui.GuiEvents.TAG_ALL_LISTS_UPDATE,
                {"track_layout": self._scene.tag_groups.track_layout,
                "weather": self._scene.tag_groups.weather,
                "light": self._scene.tag_groups.light,
                "time_of_day": self._scene.tag_groups.time_of_day,
                "environment": self._scene.tag_groups.environment,
                "additional": self._scene.tag_groups.additional_attributes}
            )

    def _add_initial_ego_track(self):
        if len(self._scene.tracks) == 0:
            if not (self._scene.tag_groups.track_layout.count("unknown") or self._scene.tag_groups.additional_attributes.count("duplicate")):
                self._scene.add_track(scene.target.TrackPosition.EGO, self._cfg.data.rail_width)
                self._gui_event.post(gui.GuiEvents.TRACK_LIST_UPDATE, self._scene.tracks.values(), 0)
                self._gui_event.post(gui.GuiEvents.TRACK_SELECT, 0)
                self._gui_event.post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def _load_scene(self) -> None:
        """
        Load scene objects from dataset.
        """
        self._image = self._dataset[self._data_counter].image
        if self._dataset[self._data_counter].annotation is None:
            self._scene = scene.Scene()
        else:
            self._scene = self._scene_deserializer.de_serialize(
                self._dataset[self._data_counter].annotation
            )

    def _save_scene(self) -> None:
        """
        Save scene object to dataset.
        Remove single points made for switches.
        Remove ego track without marks
        """
        uncompleted_switches = [switch_id for switch_id in self._scene.switches if
                                len(self._scene.switches[switch_id].marks) == 1]
        for switch_id in uncompleted_switches:
            self._scene.switches[switch_id]._marks = []

        empty_ego_tracks = [track_id for track_id in self._scene.tracks if
                        (len(self._scene.tracks[track_id].left_rail.marks)+len(self._scene.tracks[track_id].right_rail.marks)) == 0 and
                        self._scene.tracks[track_id].position == "ego"]
        for track_id in empty_ego_tracks:
            self._scene.del_track(track_id)

        annotations: dict = self._scene_deserializer.serialize(self._scene)
        self._dataset.write_annotations(annotations, self._data_counter, self._cfg)


    def _exit_annotator(self, exit_: bool) -> None:
        """
        Interrupt the annotation loop.
        :param exit_: Exit if true
        """
        self._save_scene()
        self._exit = exit_

    def _load_strategy(self, strategy: AnnotationStrategies) -> None:
        """
        Load strategy to annotate specific kind object.
        :param strategy: Annotation strategy
        """
        if strategy.value == AnnotationStrategies.TRACK.value:
            self._strategy_handler = TrackAnnotator(
                self._scene,
                self._camera,
                self._gui_event,
                self._cfg,
                self._qt_scene
            )

            for key, switch in self._scene.switches.items():
                if (switch.selected == True):
                    switch.selected = False
                    break
        elif strategy.value == AnnotationStrategies.SWITCH.value:
            self._strategy_handler = OpenCVSwitchAnnotator(
                self._scene,
                self._camera,
                self._gui_event,
                self._cfg,
                self._qt_scene,
            )
            for key, track in self._scene.tracks.items():
                if (track.selected == True):
                    track.selected = False
                    break
        else:
            print('fail strategy')
        self._strategy = strategy

        # Tags strategy is loaded in ether way
        self._tag_annotator = TagAnnotator(self._scene, self._gui_event)
        self._tag_annotator.update_gui()

    def get_eventhub(self) -> utils.IEventHub:
        return self._gui_event

    def get_scene(self) -> scene.Scene:
        return self._scene

    def get_strategy_handler(self) -> Optional[AnnotationStrategies]:
        return self._strategy_handler

    def get_datacounter(self) -> int:
        return self._data_counter

    def get_mouse(self) -> gui.IMouse:
        return self._mouse

    def update_annotations(self) -> None:
        # self._image = self._image_original.copy()
        self._scene = self._strategy_handler(
            self._image,
            self._mouse.position,
        )
        self._scene = self._tag_annotator()

    def draw_aim_device(self) -> None:
        self._strategy_handler._draw_aiming_device(
            self._image,
            self._mouse.position)


class TagAnnotator(Annotator):
    """
    Annotate tags in tag groups on the scene.
    """

    def __init__(
            self,
            scene_: scene.IScene,
            gui_event: utils.IEventHub,
    ) -> None:
        self._scene: scene.IScene = scene_
        self._gui_event: utils.IEventHub = gui_event

        # Subscribe gui events
        self._gui_event.subscribe(
            gui.GuiEvents.TAG_TRACK_LAYOUT, self._tags_track_layout
        )
        self._gui_event.subscribe(gui.GuiEvents.TAG_WEATHER, self._tags_weather)
        self._gui_event.subscribe(gui.GuiEvents.TAG_LIGHT, self._tags_light)
        self._gui_event.subscribe(gui.GuiEvents.TAG_TIME_OF_DAY, self._tags_time_of_day)
        self._gui_event.subscribe(gui.GuiEvents.TAG_ENVIRONMENT, self._tags_environment)
        self._gui_event.subscribe(gui.GuiEvents.TAG_ADDITIONAL, self._tags_additional)

    def __del__(self):
        self._gui_event.unsubscribe_all(self._tags_track_layout)
        self._gui_event.unsubscribe_all(self._tags_weather)
        self._gui_event.unsubscribe_all(self._tags_light)
        self._gui_event.unsubscribe_all(self._tags_time_of_day)
        self._gui_event.unsubscribe_all(self._tags_additional)

    def __call__(self) -> scene.IScene:
        return self._scene

    def update_gui(self) -> None:
        """
        Update elements from scene on GUI.
        """
        self._gui_event.post(
                gui.GuiEvents.TAG_ALL_LISTS_UPDATE,
                {"track_layout": self._scene.tag_groups.track_layout,
                "weather": self._scene.tag_groups.weather,
                "light": self._scene.tag_groups.light,
                "time_of_day": self._scene.tag_groups.time_of_day,
                "environment": self._scene.tag_groups.environment,
                "additional": self._scene.tag_groups.additional_attributes}
            )

    def _tags_track_layout(self, tags: dict[str, bool]) -> None:
        """
        Tags represented in tag group 'Tracks Layout'
        :param tags: List of tags
        """
        self._scene.tag_groups.track_layout = tags

    def _tags_weather(self, tags: dict[str, bool]) -> None:
        """
        Tags represented in tag group 'Weather'
        :param tags: List of tags
        """
        self._scene.tag_groups.weather = tags

    def _tags_light(self, tags: dict[str, bool]) -> None:
        """
        Tags represented in tag group 'Light'
        :param tags: List of tags
        """
        self._scene.tag_groups.light = tags

    def _tags_time_of_day(self, tags: dict[str, bool]) -> None:
        """
        Tags represented in tag group 'Time Of Day'
        :param tags: List of tags
        """
        self._scene.tag_groups.time_of_day = tags

    def _tags_environment(self, tags: dict[str, bool]) -> None:
        """
        Tags represented in tag group 'Environment'
        :param tags: List of tags
        """
        self._scene.tag_groups.environment = tags

    def _tags_additional(self, tags: dict[str, bool]) -> None:
        """
        Tags represented in tag group 'Additional'
        :param tags: List of tags
        """
        self._scene.tag_groups.additional_attributes = tags


class OpenCVSwitchAnnotator(AnnotationStrategy):
    """
    AnnotationStrategy implementing the annotation of switches dependent
    on OpenCV drawing.
    """
    draw_options = []
    draw_options: list[scene.target.SwitchDrawOptions]
    draw_options = [
        scene.target.SwitchDrawOptions.MARKS,
        scene.target.SwitchDrawOptions.BOUNDING_BOX,
        scene.target.SwitchDrawOptions.TEXT_LABEL,
    ]

    def __init__(
            self,
            scene_: scene.IScene,
            camera: utils.camera.ICamera,
            gui_event: utils.IEventHub,
            cfg: config.Labels4RailsConfig,
            qt_scene,
    ) -> None:
        """
        Create composed classes and register callbacks to gui event system.
        :param scene_: Scene to manipulate
        :param camera: Image to world calculator
        :param gui_event: Event system for GUI
        :param cfg: Configuration data class
        """

        self._qt_scene = qt_scene
        self._scene: scene.IScene = scene_
        self._scene_drawer: scene.ISceneDrawer = scene.drawer.QtSceneDrawer()
        self._camera: utils.camera.ICamera = camera
        self._cfg: config.Labels4RailsConfig = cfg
        self._draw_options = OpenCVSwitchAnnotator.draw_options

        self._aim_device: gui.aiming_devices.ICrossHair
        self._aim_device = gui.aiming_devices.CrossHair(cfg.aiming_devices.cross_hair)
        self._aim_device_drawer: QtCrossHairDrawer
        self._aim_device_drawer = QtCrossHairDrawer()

        self._gui_event: utils.IEventHub = gui_event
        self._active_target_id: Optional[int] = None

        # Post GUI events
        self._gui_event.post(
            gui.GuiEvents.SWITCH_LIST_UPDATE, self._scene.switches.values()
        )

        # Subscribe GUI events
        self._gui_event.subscribe(gui.GuiEvents.MARK, self._set_mark)
        self._gui_event.subscribe(gui.GuiEvents.REMOVE, self._del_mark)
        self._gui_event.subscribe(gui.GuiEvents.SWITCH_FORK_RIGHT, self._add_fork_right)
        self._gui_event.subscribe(gui.GuiEvents.SWITCH_FORK_LEFT, self._add_fork_left)
        self._gui_event.subscribe(
            gui.GuiEvents.SWITCH_FORK_UNKNOWN, self._add_fork_unknown
        )
        self._gui_event.subscribe(
            gui.GuiEvents.SWITCH_MERGE_RIGHT,
            self._add_merge_right,
        )
        self._gui_event.subscribe(gui.GuiEvents.SWITCH_MERGE_LEFT, self._add_merge_left)
        self._gui_event.subscribe(
            gui.GuiEvents.SWITCH_MERGE_UNKNOWN, self._add_merge_unknown
        )
        self._gui_event.subscribe(
            gui.GuiEvents.SWITCH_UNKNOWN_LEFT, self._add_unknown_left
        )
        self._gui_event.subscribe(
            gui.GuiEvents.SWITCH_UNKNOWN_RIGHT, self._add_unknown_right
        )
        self._gui_event.subscribe(
            gui.GuiEvents.SWITCH_UNKNOWN_UNKNOWN, self._add_unknown_unknown
        )
        self._gui_event.subscribe(gui.GuiEvents.SWITCH_DELETE, self._del_switch)
        self._gui_event.subscribe(gui.GuiEvents.SWITCH_SELECT, self._select_switch)
        self._gui_event.subscribe(gui.GuiEvents.SWITCH_SHOW_BOX, self._set_show_box)
        self._gui_event.subscribe(gui.GuiEvents.SWITCH_SHOW_MARKS, self._set_show_marks)
        self._gui_event.subscribe(gui.GuiEvents.SWITCH_SHOW_TEXT, self._set_show_text)
        self._gui_event.subscribe(gui.GuiEvents.SWITCH_CHANGE_SWITCH, self._change_switch)
        self._last_selected_switch = -1

    def __del__(self) -> None:
        """
        Unsubscribe gui events.
        """
        self._gui_event.unsubscribe_all(self._set_mark)
        self._gui_event.unsubscribe_all(self._del_mark)
        self._gui_event.unsubscribe_all(self._add_fork_right)
        self._gui_event.unsubscribe_all(self._add_fork_left)
        self._gui_event.unsubscribe_all(self._add_merge_right)
        self._gui_event.unsubscribe_all(self._add_merge_left)
        self._gui_event.unsubscribe_all(self._add_unknown_left)
        self._gui_event.unsubscribe_all(self._add_unknown_right)
        self._gui_event.unsubscribe_all(self._add_fork_unknown)
        self._gui_event.unsubscribe_all(self._add_merge_unknown)
        self._gui_event.unsubscribe_all(self._add_unknown_unknown)
        self._gui_event.unsubscribe_all(self._del_switch)
        self._gui_event.unsubscribe_all(self._select_switch)
        self._gui_event.unsubscribe_all(self._set_show_box)
        self._gui_event.unsubscribe_all(self._set_mark)
        self._gui_event.unsubscribe_all(self._set_show_text)
        self._gui_event.unsubscribe_all(gui.GuiEvents.SWITCH_CHANGE_SWITCH)

    def __call__(
            self,
            image: npt.NDArray[np.uint8],
            position: utils.geometry.IImagePoint,
    ) -> scene.IScene:
        """
        :param image: Image to draw on
        :param position: Point of mouse
        :return: Scene with manipulated annotations
        """
        self._draw_scene(image)
        self._draw_aiming_device(image, position)
        return self._scene

    def _draw_scene(self, image: npt.NDArray[np.uint8]) -> None:
        """
        Draw object in scene on image.
        :param image: Image to draw on
        """
        self._scene_drawer.draw_scene(
            image, self._scene, self._cfg, self._camera, self._qt_scene, *self._draw_options
        )

    def _draw_aiming_device(
            self,
            image: npt.NDArray[np.uint8],
            position: utils.geometry.IImagePoint,
    ) -> None:
        """
        Draw Aiming device on image.
        :param image: Image to draw on
        :param position: Point of mouse
        """
        width: int = image.shape[1]
        height: int = image.shape[0]
        self._aim_device.refresh(position, width, height)
        self._aim_device_drawer.draw(
            image,
            self._aim_device,
            self._cfg.aiming_devices.cross_hair,
            self._qt_scene,
            position
        )

    # def refresh_aim_device_pos(self, position: utils.geometry.IImagePoint, image: npt.NDArray[np.uint8]) -> None:
    #     # no use, refresh is done in drawer

    #     # width: int = image.shape[1]
    #     # height: int = image.shape[0]
    #     # self._aim_device.refresh(position, width, height)
    #     pass

    def _set_mark(self) -> None:
        """
        Set mark on position the aim device points to for active
        object on scene.
        """

        if self._active_target_id is not None:
            switch: scene.target.ISwitch
            switch = self._scene.switches[self._active_target_id]
            switch.add_mark(self._aim_device.points)

    def _del_mark(self) -> None:
        """
        Delete mark on position the aim device points to for active
        object on scene.
        """
        if self._active_target_id is not None:
            switch: scene.target.ISwitch
            switch = self._scene.switches[self._active_target_id]
            switch.del_mark(self._aim_device.points)

    def _add_fork_right(self) -> None:
        """
        Add switch object of kind fork and direction right to scene.
        """
        self._scene.add_switch(
            scene.target.SwitchKind.FORK,
            scene.target.SwitchDirection.RIGHT,
        )
        self._gui_event.post(
            gui.GuiEvents.SWITCH_LIST_UPDATE, self._scene.switches.values()
        )

    def _add_fork_left(self) -> None:
        """
        Add switch object of kind fork and direction left to scene.
        """
        self._scene.add_switch(
            scene.target.SwitchKind.FORK,
            scene.target.SwitchDirection.LEFT,
        )
        self._gui_event.post(
            gui.GuiEvents.SWITCH_LIST_UPDATE,
            self._scene.switches.values(),
        )

    def _add_fork_unknown(self) -> None:
        """
        Add switch object of kind fork and direction unknown to scene.
        """
        self._scene.add_switch(
            scene.target.SwitchKind.FORK,
            scene.target.SwitchDirection.UNKNOWN,
        )
        self._gui_event.post(
            gui.GuiEvents.SWITCH_LIST_UPDATE,
            self._scene.switches.values(),
        )

    def _add_merge_left(self) -> None:
        """
        Add switch object of kind merge and direction left to scene.
        """
        self._scene.add_switch(
            scene.target.SwitchKind.MERGE,
            scene.target.SwitchDirection.LEFT,
        )
        self._gui_event.post(
            gui.GuiEvents.SWITCH_LIST_UPDATE,
            self._scene.switches.values(),
        )

    def _add_merge_right(self) -> None:
        """
        Add switch object of kind merge and direction right to scene.
        """
        self._scene.add_switch(
            scene.target.SwitchKind.MERGE,
            scene.target.SwitchDirection.RIGHT,
        )
        self._gui_event.post(
            gui.GuiEvents.SWITCH_LIST_UPDATE,
            self._scene.switches.values(),
        )

    def _add_merge_unknown(self) -> None:
        """
        Add switch object of kind merge and direction unknown to scene.
        """
        self._scene.add_switch(
            scene.target.SwitchKind.MERGE,
            scene.target.SwitchDirection.UNKNOWN,
        )
        self._gui_event.post(
            gui.GuiEvents.SWITCH_LIST_UPDATE,
            self._scene.switches.values(),
        )

    def _add_unknown_left(self) -> None:
        """
        Add switch object of kind unknown and direction left to scene.
        """
        self._scene.add_switch(
            scene.target.SwitchKind.UNKNOWN,
            scene.target.SwitchDirection.LEFT,
        )
        self._gui_event.post(
            gui.GuiEvents.SWITCH_LIST_UPDATE,
            self._scene.switches.values(),
        )

    def _add_unknown_right(self) -> None:
        """
        Add switch object of kind unknown and direction right to scene.
        """
        self._scene.add_switch(
            scene.target.SwitchKind.UNKNOWN,
            scene.target.SwitchDirection.RIGHT,
        )
        self._gui_event.post(
            gui.GuiEvents.SWITCH_LIST_UPDATE,
            self._scene.switches.values(),
        )

    def _add_unknown_unknown(self) -> None:
        """
        Add switch object of kind unknown and direction unknown to scene.
        """
        self._scene.add_switch(
            scene.target.SwitchKind.UNKNOWN,
            scene.target.SwitchDirection.UNKNOWN,
        )
        self._gui_event.post(
            gui.GuiEvents.SWITCH_LIST_UPDATE,
            self._scene.switches.values(),
        )

    def _del_switch(self) -> None:
        """
        Delete active switch object from scene.
        """
        if self._active_target_id is not None:
            self._scene.del_switch(self._active_target_id)
        self._gui_event.post(
            gui.GuiEvents.SWITCH_LIST_UPDATE,
            self._scene.switches.values(),
        )

    def _change_switch(self, switch_id: int, switch_kind: target.SwitchKind,
                       switch_direction: target.SwitchDirection, ) -> None:
        """
        Change the kind and direction of specified switch
        :param switch_id: switch that will be edited
        :param switch_kind: new kind of the switch
        :param switch_direction: new direction of the switch
        """
        if switch_id in self._scene.switches:
            self._scene.edit_switch(switch_id, switch_kind, switch_direction)
            self._scene.switches[switch_id].selected = False
            self._gui_event.post(
                gui.GuiEvents.SWITCH_LIST_UPDATE, self._scene.switches.values()
            )

    def _select_switch(self, switch_id: int) -> None:
        """
        Set switch object as active target object.
        """
        if switch_id in self._scene.switches:
            self._active_target_id = switch_id
            if self._last_selected_switch != -1 and self._last_selected_switch in self._scene.switches:
                self._scene.switches[self._last_selected_switch].selected = False

            self._scene.switches[switch_id].selected = True
            self._last_selected_switch = switch_id
        else:
            self._active_target_id = None

    def _set_show_marks(self, marks: bool) -> None:
        """
        Set whether the marks are to be displayed.
        :param marks: Display state
        """
        if marks and scene.target.SwitchDrawOptions.MARKS not in self._draw_options:
            self._draw_options.append(scene.target.SwitchDrawOptions.MARKS)
        elif not marks:
            while scene.target.SwitchDrawOptions.MARKS in self._draw_options:
                self._draw_options.remove(scene.target.SwitchDrawOptions.MARKS)

    def _set_show_box(self, box: bool) -> None:
        """
        Set whether the bounding box is to be displayed.
        :param box: Display state
        """
        if (
                box
                and scene.target.SwitchDrawOptions.BOUNDING_BOX not in self._draw_options
        ):
            self._draw_options.append(scene.target.SwitchDrawOptions.BOUNDING_BOX)
        elif not box:
            while scene.target.SwitchDrawOptions.BOUNDING_BOX in self._draw_options:
                self._draw_options.remove(scene.target.SwitchDrawOptions.BOUNDING_BOX)

    def _set_show_text(self, text: bool) -> None:
        """
        Set whether the switch id label text is to be displayed.
        :param text: Display state
        """
        if text and scene.target.SwitchDrawOptions.TEXT_LABEL not in self._draw_options:
            self._draw_options.append(scene.target.SwitchDrawOptions.TEXT_LABEL)
        elif not text:
            while scene.target.SwitchDrawOptions.TEXT_LABEL in self._draw_options:
                self._draw_options.remove(scene.target.SwitchDrawOptions.TEXT_LABEL)


class TrackAnnotator(AnnotationStrategy):
    """
    AnnotationStrategy implementing the annotation of tracks dependent
    on OpenCV drawing.
    """
    draw_options = []
    draw_options: list[
        Union[
            scene.target.RailDrawOptions,
            scene.target.TrackBedDrawOptions,
        ]
    ]
    draw_options = [
        scene.target.RailDrawOptions.MARKS,
        scene.target.RailDrawOptions.CONTOUR,
        scene.target.TrackBedDrawOptions.CONTOUR,
    ]

    def __init__(
            self,
            scene_: scene.IScene,
            camera: utils.camera.ICamera,
            gui_event: utils.IEventHub,
            cfg: config.Labels4RailsConfig,
            qt_scene,
    ) -> None:
        """
        Create composed classes and register callbacks to gui event system.
        :param scene_: Scene to manipulate
        :param camera: Image to world calculator
        :param gui_event: Event system for GUI
        :param cfg: Configuration data class
        :param last_selected: Save the last selected Track in scene
        """
        self._qt_scene = qt_scene
        self._scene: scene.IScene = scene_
        self._scene_drawer: scene.ISceneDrawer = scene.drawer.QtSceneDrawer()
        self._camera: utils.camera.ICamera = camera
        self._cfg: config.Labels4RailsConfig = cfg
        self._draw_options = TrackAnnotator.draw_options
        self._aim_device: gui.aiming_devices.ITrackStencil
        self._aim_device = gui.aiming_devices.TrackStencil(cfg.aiming_devices.track_stencil, camera)
        self._aim_device_drawer: QtTrackStencilDrawer
        self._aim_device_drawer = QtTrackStencilDrawer()
        self._gui_event: utils.IEventHub = gui_event
        self._active_target_id: Optional[int] = None
        self._gui_event.subscribe(gui.GuiEvents.INDEPENDENT_MODE, self._independent_mode)
        # Post event
        self._gui_event.post(
            gui.GuiEvents.TRACK_LIST_UPDATE, self._scene.tracks.values(), -2
        )

        # Subscribe GUI events
        self._gui_event.subscribe(gui.GuiEvents.MARK, self._set_mark)
        self._gui_event.subscribe(gui.GuiEvents.REMOVE, self._del_mark)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_CREATE_EGO, self._add_ego)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_CREATE_LEFT, self._add_left)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_CREATE_RIGHT, self._add_right)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_DELETE, self._del_track)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_SELECT, self._select_track)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_CHANGE_POSITION, self._change_track_position)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_MARKS, self._show_marks)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_SPLINES, self._show_splines)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_CONTOUR, self._show_contour)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_FILL, self._show_fill)
        if self._aim_device.label_mode == "side_point":
            self._gui_event.subscribe(gui.GuiEvents.TRACK_WIDTH_INCR, self._stencil_width)
            self._gui_event.subscribe(gui.GuiEvents.TRACK_WIDTH_DECR, self._stencil_width)
        else:
            self._gui_event.subscribe(gui.GuiEvents.TRACK_WIDTH_INCR, self._set_independent_mark_right)
            self._gui_event.subscribe(gui.GuiEvents.TRACK_WIDTH_DECR, self._set_independent_mark_left)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_ANGLE_INCR, self._stencil_angle)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_ANGLE_DECR, self._stencil_angle)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_STENCIL_SIDE, self._stencil_side)
        self._gui_event.subscribe(gui.GuiEvents.DRAG, self._drag)
        self._gui_event.subscribe(gui.GuiEvents.DROP, self._drop)

        self._last_selected_track: int = -1

        self._removed_rail_mark = None
        self._removed_rail_id = None
        self._removed_rail_index = None
        self._removed_rail_index_opposite = None

        self._last_stencil_color = self._cfg.aiming_devices.track_stencil["color"]
        self._drag_color = [255, 0, 0]
        self._mode_locked = False

    def __del__(self) -> None:
        """
        Unsubscribe gui events.
        """
        self._gui_event.unsubscribe_all(self._set_mark)
        self._gui_event.unsubscribe_all(self._del_mark)
        self._gui_event.unsubscribe_all(self._add_ego)
        self._gui_event.unsubscribe_all(self._add_left)
        self._gui_event.unsubscribe_all(self._add_right)
        self._gui_event.unsubscribe_all(self._del_track)
        self._gui_event.unsubscribe_all(self._select_track)
        self._gui_event.unsubscribe_all(self._change_track_position)
        self._gui_event.unsubscribe_all(self._show_marks)
        self._gui_event.unsubscribe_all(self._show_splines)
        self._gui_event.unsubscribe_all(self._show_contour)
        self._gui_event.unsubscribe_all(self._show_fill)
        self._gui_event.unsubscribe_all(self._stencil_width)
        self._gui_event.unsubscribe_all(self._stencil_angle)
        self._gui_event.unsubscribe_all(self._stencil_side)
        self._gui_event.unsubscribe_all(self._drag)
        self._gui_event.unsubscribe_all(self._drop)

    def __call__(
            self,
            image: npt.NDArray[np.uint8],
            position: utils.geometry.IImagePoint,
    ) -> scene.IScene:
        """
        :param image: Image to draw on
        :param position: Center point of aim device
        :return: Scene with manipulated annotations
        """

        self._draw_scene(image, self._camera)
        self._draw_aiming_device(image, position)
        return self._scene

    def _independent_mode(self):
        """
        Changes the mode of the stencil on key "w"
        """
        if not self._mode_locked:
            if self._aim_device.label_mode == "side_point":
                self._aim_device.label_mode = "independent_mode"
                self._gui_event.unsubscribe_all(self._stencil_width)
                self._gui_event.subscribe(gui.GuiEvents.TRACK_WIDTH_INCR, self._set_independent_mark_right)
                self._gui_event.subscribe(gui.GuiEvents.TRACK_WIDTH_DECR, self._set_independent_mark_left)
            else:
                self._aim_device.label_mode = "side_point"

                self._gui_event.subscribe(gui.GuiEvents.TRACK_WIDTH_INCR, self._stencil_width)
                self._gui_event.subscribe(gui.GuiEvents.TRACK_WIDTH_DECR, self._stencil_width)

    def _draw_scene(
            self,
            image: npt.NDArray[np.uint8],
            camera: utils.camera.ICamera,
    ) -> None:
        """
        Draw object in scene on image.
        :param image: Image to draw on
        """
        self._scene_drawer.draw_scene(
            image, self._scene, self._cfg, camera, self._qt_scene, *self._draw_options
        )

    def _draw_aiming_device(
            self,
            image: npt.NDArray[np.uint8],
            position: utils.geometry.IImagePoint,
    ) -> None:
        """
        Draw Aiming device on image.
        :param image: Image to draw on
        :param position: Point of mouse
        """
        self._aim_device.refresh(position)
        self._aim_device_drawer.draw(
            image, self._aim_device,
            self._cfg.aiming_devices.track_stencil,
            self._qt_scene,
            position,
            drag_color=self._drag_color,
            flag=self._check_nearest_point(position),

        )
        self._aim_device_drawer.update(
            self._aim_device,
            self._qt_scene)

    def _set_mark(self) -> None:
        """
        Set mark on position the aim device points to for active
        object on scene.
        """
        if self._active_target_id is not None:
            if self._aim_device.label_mode == "side_point":
                img_size = self._qt_scene.get_image_size()
                if ((self._aim_device.right_point.x >= -1 and self._aim_device.right_point.x < img_size.width()+1) and (
                    self._aim_device.right_point.y >= -1 and self._aim_device.right_point.y < img_size.height()+1)) or (
                    (self._aim_device.left_point.x >= -1 and self._aim_device.left_point.x < img_size.width()+1) and (
                    self._aim_device.left_point.y >= -1 and self._aim_device.left_point.y < img_size.height()+1)):

                    track: scene.target.ITrack = self._scene.tracks[self._active_target_id]
                    track.add_mark([self._aim_device.left_point, self._aim_device.right_point])

    def _set_independent_mark_right(self, width_delta: int):
        """
        Sets marker on left rail if no rail was set yet
        :param width_delta is necessary to avoid conflict with the _stencil_width method (both are on key "a")
        """
        if self._active_target_id is not None:
            img_size = self._qt_scene.get_image_size()
            if self._aim_device.right_point.x >= -1 and self._aim_device.right_point.x < img_size.width()+1 and (
                self._aim_device.right_point.y >= -1 and self._aim_device.right_point.y < img_size.height()+1):

                track: scene.target.ITrack = self._scene.tracks[self._active_target_id]
                track.right_rail.add_mark(self._aim_device.right_point)

    def _set_independent_mark_left(self, width_delta: int):
        """
        Sets marker on right rail if no rail was set yet
        :param width_delta is necessary to avoid conflict with the _stencil_width method (both are on key "d")
        """

        if self._active_target_id is not None:
            img_size = self._qt_scene.get_image_size()
            if self._aim_device.left_point.x >= -1 and self._aim_device.left_point.x < img_size.width()+1 and (
                self._aim_device.left_point.y >= -1 and self._aim_device.left_point.y < img_size.height()+1):

                track: scene.target.ITrack = self._scene.tracks[self._active_target_id]
                track.left_rail.add_mark(self._aim_device.left_point)

    def _del_mark(self) -> None:
        """
        Delete mark on position the aim device points to for active
        object on scene.
        Lead index is side of the stencil on which follows the mouse.
        If the stencil is in the independent mode remove incomplete marker (left point or right point is missing)

        """
        if self._active_target_id is not None and self._empty_tracks(self._active_target_id) == False:
            track: scene.target.ITrack = self._scene.tracks[self._active_target_id]
            if self._aim_device.label_mode == "side_point":
                if self._aim_device.aim_rail == gui.aiming_devices.track_stencil.AimRail.RIGHT:
                    mark_index, railSide = track.get_nearest_mark(self._aim_device.right_point)
                    track.del_mark(self._aim_device.right_point)
                    if mark_index >= 0 and railSide == target.track.rail.RailSide.RIGHT:
                        track.del_mark(self._aim_device.left_point)
                else:
                    mark_index, railSide = track.get_nearest_mark(self._aim_device.left_point)
                    track.del_mark(self._aim_device.left_point)
                    if mark_index >= 0 and railSide == target.track.rail.RailSide.LEFT:
                        track.del_mark(self._aim_device.right_point)
            else:
                track.del_mark(self._aim_device.left_point)

    def _add_ego(self) -> None:
        """
        Add track object of kind ego to scene.
        """
        # There may only be one ego track
        tracks_positions: list[scene.target.TrackPosition]
        tracks_positions = [track.position for track in self._scene.tracks.values()]
        if scene.target.TrackPosition.EGO in tracks_positions:
            return
        else:
            self._scene.add_track(
                scene.target.TrackPosition.EGO, self._cfg.data.rail_width
            )
        self._gui_event.post(
            gui.GuiEvents.TRACK_LIST_UPDATE, self._scene.tracks.values(), -1
        )

    def _add_left(self) -> None:
        """
        Add track object of kind 'left to ego' to scene.
        """
        self._scene.add_track(
            scene.target.TrackPosition.LEFT, self._cfg.data.rail_width
        )
        self._gui_event.post(
            gui.GuiEvents.TRACK_LIST_UPDATE, self._scene.tracks.values(), -1
        )

    def _add_right(self) -> None:
        """
        Add track object of kind 'right to ego' to scene.
        """
        self._scene.add_track(
            scene.target.TrackPosition.RIGHT, self._cfg.data.rail_width
        )
        self._gui_event.post(
            gui.GuiEvents.TRACK_LIST_UPDATE, self._scene.tracks.values(), -1
        )

    def _del_track(self) -> None:
        """
        Delete active track object from scene.
        """
        if self._active_target_id is not None:
            self._scene.del_track(self._active_target_id)
            self._active_target_id = None
        self._gui_event.post(
            gui.GuiEvents.TRACK_LIST_UPDATE, self._scene.tracks.values(), -2
        )

    def _select_track(self, track_id: int) -> None:

        """
        Set track object as active target object and mark the track as  is as selected.
        """
        if track_id in self._scene.tracks:
            self._active_target_id = track_id

            if self._last_selected_track != -1 and self._last_selected_track in self._scene.tracks:
                self._scene.tracks[self._last_selected_track].selected = False

            self._scene.tracks[track_id].selected = True
            self._last_selected_track = track_id

        else:
            self._active_target_id = None

    def _change_track_position(self, track_id: int, track_position: target.TrackPosition):
        """
        Change the position of the selected track
        :param track_id: if of the track that will be edited
        :param track_position: new position of the track
        """
        if track_id in self._scene.tracks:
            self._scene.edit_track(track_id, track_position)
            self._gui_event.post(
                gui.GuiEvents.TRACK_LIST_UPDATE, self._scene.tracks.values(), track_id
            )


    def _show_marks(self, marks: bool) -> None:
        """
        Set whether the marks are to be displayed.
        :param marks: Display state
        """
        if marks and scene.target.RailDrawOptions.MARKS not in self._draw_options:
            self._draw_options.append(scene.target.track.RailDrawOptions.MARKS)
        elif not marks:
            while scene.target.RailDrawOptions.MARKS in self._draw_options:
                self._draw_options.remove(scene.target.RailDrawOptions.MARKS)

    def _show_splines(self, splines: bool) -> None:
        """
        Set whether the spline points are to be displayed.
        :param splines: Display state
        """
        if splines and scene.target.RailDrawOptions.SPLINES not in self._draw_options:
            self._draw_options.append(scene.target.RailDrawOptions.SPLINES)
        elif not splines:
            while scene.target.RailDrawOptions.SPLINES in self._draw_options:
                self._draw_options.remove(scene.target.RailDrawOptions.SPLINES)

    def _show_contour(self, contour: bool) -> None:
        """
        Set whether the contour is to be displayed.
        :param contour: Display state
        """
        if contour and scene.target.RailDrawOptions.CONTOUR not in self._draw_options:
            self._draw_options.append(scene.target.RailDrawOptions.CONTOUR)
        elif not contour:
            while scene.target.RailDrawOptions.CONTOUR in self._draw_options:
                self._draw_options.remove(scene.target.RailDrawOptions.CONTOUR)
        if (
                contour
                and scene.target.TrackBedDrawOptions.CONTOUR not in self._draw_options
        ):
            self._draw_options.append(scene.target.TrackBedDrawOptions.CONTOUR)
        elif not contour:
            while scene.target.TrackBedDrawOptions.CONTOUR in self._draw_options:
                self._draw_options.remove(scene.target.TrackBedDrawOptions.CONTOUR)

    def _show_fill(self, fill: bool) -> None:
        """
        Set whether the filled contour is to be displayed.
        :param fill: Display state
        """
        if fill and scene.target.RailDrawOptions.FILL not in self._draw_options:
            self._draw_options.append(scene.target.RailDrawOptions.FILL)
        elif not fill:
            while scene.target.RailDrawOptions.FILL in self._draw_options:
                self._draw_options.remove(scene.target.RailDrawOptions.FILL)
        if fill and scene.target.TrackBedDrawOptions.FILL not in self._draw_options:
            self._draw_options.append(scene.target.TrackBedDrawOptions.FILL)
        elif not fill:
            while scene.target.TrackBedDrawOptions.FILL in self._draw_options:
                self._draw_options.remove(scene.target.TrackBedDrawOptions.FILL)

    def _stencil_width(self, width_delta: int) -> None:
        """
        Increment or decrement the aim device in steps of pixel on
        the 2D image plane.
        :param width_delta: Width increment / decrement
        """
        self._aim_device.incr_width(width_delta)

    def _stencil_angle(self, angle_delta: int) -> None:
        """
        Increment or decrement the aim device angle in decree steps.
        :param angle_delta:  Angle increment / decrement
        """
        self._aim_device.incr_angle(angle_delta)

    def _stencil_side(self) -> None:
        """
        Change the point of stencil which follows the mouse pointer.
        """
        self._aim_device.toggle()

    def _empty_tracks(self, track_id):
        track: scene.target.ITrack = self._scene.tracks[track_id]
        return len(track.left_rail.marks) == 0 and len(track.right_rail.marks) == 0

    def _check_nearest_point(self, position: utils.geometry.IImagePoint):
        """
        checks if any point is near the current mouser position
        :param position of the mouse
        """
        if self._active_target_id is not None:
            track = self._scene.tracks[self._active_target_id]
            left_rail = track.left_rail.marks
            right_rail = track.right_rail.marks
            cutoff = 5
            for point in left_rail + right_rail:
                dist = math.dist(position.point, point.point)

                if dist <= cutoff:
                    return True

        return False

    def _drag(self, pos):
        """
        Information: The aiming device turns in to the color of self._drag_color if it is above a mark.

        This method removes on right click (hold) the point of a rail of the selected track and changes the color of the
        aiming device to the one specified in self._drag_color to create an illusion of drag and drop.
        @param pos: position of the aiming device
        """
        if self._active_target_id is not None:
            if self._aim_device.label_mode == "independent_mode":
                track = self._scene.tracks[self._active_target_id]

                position: utils.geometry.IImagePoint
                position = utils.geometry.ImagePoint(pos.x(), pos.y())

                mark_index, railSide = track.get_nearest_mark(position)

                if mark_index >= 0:
                    self._removed_rail_index = mark_index
                    self._removed_rail_id = self._active_target_id
                    if railSide == target.track.rail.RailSide.LEFT:
                        self._removed_rail_mark = "left"
                        track.left_rail.del_mark(mark_index=mark_index)

                    elif railSide == target.track.rail.RailSide.RIGHT:
                        self._removed_rail_mark = "right"
                        track.right_rail.del_mark(mark_index=mark_index)

                    self._cfg.aiming_devices.track_stencil["color"] = self._drag_color
                    self._mode_locked = True
            else:
                track = self._scene.tracks[self._active_target_id]
                position: utils.geometry.IImagePoint
                position = utils.geometry.ImagePoint(pos.x(), pos.y())

                mark_index, railSide = track.get_nearest_mark(position)

                if mark_index >= 0:
                    if railSide == target.track.rail.RailSide.LEFT:#left_mark is not None:
                        self._removed_rail_index = mark_index
                        self._removed_rail_id = self._active_target_id
                        self._removed_rail_mark = "left"
                        track.left_rail.del_mark(mark_index=mark_index)
                        if self._aim_device.aim_rail.name == "LEFT":
                            mark_index_opposite, railSide_opposite = track.get_nearest_mark(self._aim_device.right_point)
                            if mark_index_opposite >= 0 and railSide_opposite == target.track.rail.RailSide.RIGHT:
                                track.right_rail.del_mark(mark_index=mark_index_opposite)
                                self._removed_rail_index_opposite = mark_index_opposite

                    elif railSide == target.track.rail.RailSide.RIGHT:
                        self._removed_rail_index = mark_index
                        self._removed_rail_id = self._active_target_id
                        self._removed_rail_mark = "right"
                        track.right_rail.del_mark(mark_index=mark_index)
                        if self._aim_device.aim_rail.name == "RIGHT":
                            mark_index_opposite, railSide_opposite = track.get_nearest_mark(self._aim_device.left_point)
                            if mark_index_opposite >= 0 and railSide_opposite == target.track.rail.RailSide.LEFT:
                                track.left_rail.del_mark(mark_index=mark_index_opposite)
                                self._removed_rail_index_opposite = mark_index_opposite
                    self._cfg.aiming_devices.track_stencil["color"] = self._drag_color
                    self._mode_locked = True

    def _drop(self, pos):
        """
        This method places on right click (release) a mark on the current position of the mouse.
        The mark will be placed at the same index of the rail as the removed mark in self._drag.
        @param pos: position of the aiming device.
        """
        self._cfg.aiming_devices.track_stencil["color"] = self._last_stencil_color
        if self._active_target_id is not None and self._removed_rail_id is not None:
            track = self._scene.tracks[self._removed_rail_id]
            point: utils.geometry.IImagePoint
            point = utils.geometry.ImagePoint(pos.x(), pos.y())
            if self._removed_rail_mark is not None and self._removed_rail_mark == "right":
                track.right_rail.marks.insert(self._removed_rail_index, point)
                if self._removed_rail_index_opposite is not None:
                     track.left_rail.marks.insert(self._removed_rail_index_opposite, self._aim_device.left_point)
                self._mode_locked = False

            elif self._removed_rail_mark is not None and self._removed_rail_mark == "left":
                track.left_rail.marks.insert(self._removed_rail_index, point)
                if self._removed_rail_index_opposite is not None:
                     track.right_rail.marks.insert(self._removed_rail_index_opposite, self._aim_device.right_point)
                self._mode_locked = False

            self._removed_rail_id = None
            self._removed_rail_index = None
            self._removed_rail_index_opposite = None
            self._removed_rail_mark = None
