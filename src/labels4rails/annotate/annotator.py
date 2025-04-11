import abc
import scene
import data
import enum
import gui
import utils
import numpy as np
import numpy.typing as npt

from utils import config
from typing import Optional, Union

from src.scene import target
from src.scene.target import SwitchDirection


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
        self._update_gui()

    def __del__(self):
        self._gui_event.unsubscribe_all(self._tags_track_layout)
        self._gui_event.unsubscribe_all(self._tags_weather)
        self._gui_event.unsubscribe_all(self._tags_light)
        self._gui_event.unsubscribe_all(self._tags_time_of_day)
        self._gui_event.unsubscribe_all(self._tags_additional)

    def __call__(self) -> scene.IScene:
        return self._scene

    def _update_gui(self) -> None:
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
    ) -> None:
        """
        Create composed classes and register callbacks to gui event system.
        :param scene_: Scene to manipulate
        :param camera: Image to world calculator
        :param gui_event: Event system for GUI
        :param cfg: Configuration data class
        """
        self._scene: scene.IScene = scene_
        self._scene_drawer: scene.ISceneDrawer = scene.OpenCVSceneDrawer()
        self._camera: utils.camera.ICamera = camera
        self._cfg: config.Labels4RailsConfig = cfg
        self._draw_options = OpenCVSwitchAnnotator.draw_options
        self._aim_device: scene.aiming_devices.ICrossHair
        self._aim_device = scene.aiming_devices.CrossHair(cfg.aiming_devices.cross_hair)
        self._aim_device_drawer: scene.aiming_devices.ICrossHairDrawer
        self._aim_device_drawer = scene.aiming_devices.OpenCVCrossHairDrawer()
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
            image, self._scene, self._cfg, self._camera, *self._draw_options
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
            image, self._aim_device, self._cfg.aiming_devices.cross_hair
        )

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
        scene.target.RailDrawOptions.FILL,
        scene.target.TrackBedDrawOptions.FILL,
    ]

    def __init__(
            self,
            scene_: scene.IScene,
            camera: utils.camera.ICamera,
            gui_event: utils.IEventHub,
            cfg: config.Labels4RailsConfig,
    ) -> None:
        """
        Create composed classes and register callbacks to gui event system.
        :param scene_: Scene to manipulate
        :param camera: Image to world calculator
        :param gui_event: Event system for GUI
        :param cfg: Configuration data class
        :param last_selected: Save the last selected Track in scene
        """
        self._scene: scene.IScene = scene_
        self._scene_drawer: scene.ISceneDrawer = scene.OpenCVSceneDrawer()
        self._camera: utils.camera.ICamera = camera
        self._cfg: config.Labels4RailsConfig = cfg
        self._draw_options = TrackAnnotator.draw_options
        self._aim_device: scene.aiming_devices.ITrackStencil
        self._aim_device = scene.aiming_devices.TrackStencil(
            cfg.aiming_devices.track_stencil, camera
        )
        self._aim_device_drawer: scene.aiming_devices.ITrackStencilDrawer
        self._aim_device_drawer = scene.aiming_devices.OpenCVTrackStencilDrawer()
        self._gui_event: utils.IEventHub = gui_event
        self._active_target_id: Optional[int] = None
        self._gui_event.subscribe(gui.GuiEvents.INDEPENDENT_MODE, self._independent_mode)

        # Post event
        self._gui_event.post(
            gui.GuiEvents.TRACK_LIST_UPDATE, self._scene.tracks.values(),-2
        )

        # Subscribe GUI events
        self._gui_event.subscribe(gui.GuiEvents.MARK, self._set_mark)
        self._gui_event.subscribe(gui.GuiEvents.REMOVE, self._del_mark)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_CREATE_EGO, self._add_ego)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_CREATE_LEFT, self._add_left)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_CREATE_RIGHT, self._add_right)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_DELETE, self._del_track)
        self._gui_event.subscribe(gui.GuiEvents.TRACK_SELECT, self._select_track)
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
        self.left_point = None
        self.right_point = None
        self._last_selected_track: int = -1

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
        self._gui_event.unsubscribe_all(self._show_marks)
        self._gui_event.unsubscribe_all(self._show_splines)
        self._gui_event.unsubscribe_all(self._show_contour)
        self._gui_event.unsubscribe_all(self._show_fill)
        self._gui_event.unsubscribe_all(self._stencil_width)
        self._gui_event.unsubscribe_all(self._stencil_angle)
        self._gui_event.unsubscribe_all(self._stencil_side)

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
        if self._aim_device.label_mode == "side_point":
            self._aim_device.label_mode = "independent_mode"
            self.left_point = None
            self.right_point = None
            self._gui_event.unsubscribe_all(self._stencil_width)
            self._gui_event.subscribe(gui.GuiEvents.TRACK_WIDTH_INCR, self._set_independent_mark_right)
            self._gui_event.subscribe(gui.GuiEvents.TRACK_WIDTH_DECR, self._set_independent_mark_left)
        else:
            self._aim_device.label_mode = "side_point"
            if self.left_point is not None or self.right_point is not None:
                self._remove_incomplete_points()

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
            image, self._scene, self._cfg, camera, *self._draw_options
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
            image, self._aim_device, self._cfg.aiming_devices.track_stencil
        )

    def _set_mark(self) -> None:
        """
        Set mark on position the aim device points to for active
        object on scene.
        """
        if self._active_target_id is not None:
            if self._aim_device.label_mode == "side_point":
                track: scene.target.ITrack = self._scene.tracks[self._active_target_id]
                track.add_mark([self._aim_device.left_point, self._aim_device.right_point])

    def _set_independent_mark_right(self, width_delta: int):
        """
        Sets marker on left rail if no rail was set yet
        :param width_delta is necessary to avoid conflict with the _stencil_width method (both are on key "a")
        """
        if self._active_target_id is not None:

            if self.right_point is None:

                self.right_point = self._aim_device.right_point
                track: scene.target.ITrack = self._scene.tracks[self._active_target_id]
                track.right_rail.add_mark(self.right_point)
                if self.left_point is not None:
                    self.left_point = None
                    self.right_point = None

    def _set_independent_mark_left(self, width_delta: int):
        """
        Sets marker on right rail if no rail was set yet
        :param width_delta is necessary to avoid conflict with the _stencil_width method (both are on key "d")
        """
        if self._active_target_id is not None:
            if self.left_point is None:

                self.left_point = self._aim_device.left_point
                track: scene.target.ITrack = self._scene.tracks[self._active_target_id]
                track.left_rail.add_mark(self.left_point)
                if self.right_point is not None:
                    self.left_point = None
                    self.right_point = None

    def _del_mark(self) -> None:
        """
        Delete mark on position the aim device points to for active
        object on scene.
        Lead index is side of the stencil on which follows the mouse.
        If the stencil is in the independent mode remove incomplete marker (left point or right point is missing)

        """
        if self._active_target_id is not None:
            if self._aim_device.label_mode == "side_point":

                track: scene.target.ITrack = self._scene.tracks[self._active_target_id]
                if (
                        self._aim_device.aim_rail
                        == scene.aiming_devices.track_stencil.AimRail.LEFT
                ):
                    lead_index: int = 0
                else:
                    lead_index = 1
                track.del_mark(
                    [self._aim_device.left_point, self._aim_device.right_point],
                    lead_index,
                )
            else:

                if self.right_point is None and self.left_point is None:
                    track: scene.target.ITrack = self._scene.tracks[self._active_target_id]
                    track.del_mark(
                        [self._aim_device.left_point, self._aim_device.right_point],
                        1,
                    )

                if self.left_point is not None and self.right_point is None:
                    track: scene.target.ITrack = self._scene.tracks[self._active_target_id]
                    track.left_rail.del_mark(mark=self.left_point)
                    self.left_point = None
                if self.right_point is not None and self.left_point is None:
                    track: scene.target.ITrack = self._scene.tracks[self._active_target_id]
                    track.right_rail.del_mark(mark=self.right_point)
                    self.right_point = None

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
            self._remove_incomplete_points()
            self._active_target_id = track_id

            if self._last_selected_track != -1 and self._last_selected_track in self._scene.tracks:
                self._scene.tracks[self._last_selected_track].selected = False

            self._scene.tracks[track_id].selected = True
            self._last_selected_track = track_id

        else:
            self._active_target_id = None

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

    def _remove_incomplete_points(self):
        if self._active_target_id is not None:
            if self.left_point is not None:
                track: scene.target.ITrack = self._scene.tracks[self._active_target_id]
                track.left_rail.del_mark(mark=self.left_point)
            elif self.right_point is not None:
                track: scene.target.ITrack = self._scene.tracks[self._active_target_id]
                track.right_rail.del_mark(mark=self.right_point)
            self.left_point = None
            self.right_point = None
