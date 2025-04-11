from typing import Union, Optional
import abc
from .scene import IScene
from labels4rails.utils import camera, geometry, config
from . import target
import numpy as np
import numpy.typing as npt


class ISceneDrawer(metaclass=abc.ABCMeta):
    """
    Draw IScene objects.
    """

    @abc.abstractmethod
    def draw_scene(
        self,
        image: npt.NDArray[np.uint8],
        scene: IScene,
        cfg: config.Labels4RailsConfig,
        camera_: camera.ICamera,
        *args: Union[target.TrackBedDrawOptions, target.RailDrawOptions],
    ):
        """
        Draw IScene objects on an image.
        :param image: Image to draw on
        :param scene: IScene object
        :param cfg: Configuration data set
        :param camera_: Image to world calculator
        :param args: Drawing attributes
        :return: Image with IScene objects
        """
        pass

    @abc.abstractmethod
    def draw_tracks(
        self,
        image: npt.NDArray[np.uint8],
        tracks: list[target.ITrack],
        cfg: config.Tracks,
        camera_: camera.ICamera,
        *args: Union[target.TrackBedDrawOptions, target.RailDrawOptions],
    ) -> None:
        """
        Draw ITrack objects on image.
        :param image: Image to draw on
        :param tracks: ITrack objects to draw
        :param cfg: Configuration data class
        :param camera_: Image to world calculator
        :param args: Drawing attributes
        """
        pass

    @abc.abstractmethod
    def draw_switches(
        self,
        image: npt.NDArray[np.uint8],
        switches: list[target.ISwitch],
        cfg: config.Switches,
        aim_point: Optional[geometry.IImagePoint] = None,
        *args,
    ) -> None:
        """
        Draw ISwitch on image.
        :param image: Image to draw on
        :param switches: ISwitch object to draw
        :param cfg: Configuration data class
        :param aim_point: Where aime device points to
        :param args: Attributes of switch to draw
        """
        pass


class OpenCVSceneDrawer(ISceneDrawer):
    """
    Draw scene using OpenCV.
    """

    def __init__(self) -> None:
        self._track_drawer: target.ITrackDrawer = target.OpenCVTrackDrawer()
        self._switch_drawer: target.ISwitchDrawer = target.OpenCVSwitchDrawer()

    def draw_scene(
        self,
        image: npt.NDArray[np.uint8],
        scene: IScene,
        cfg: config.Labels4RailsConfig,
        camera_: camera.ICamera,
        *args: Union[target.TrackBedDrawOptions, target.RailDrawOptions],
    ):
        """
        Draw IScene objects on an image.
        :param image: Image to draw on
        :param scene: IScene object
        :param cfg: Configuration data set
        :param camera_: Image to world calculator
        :param args: Drawing attributes
        :return: Image with IScene objects
        """
        if cfg.targets.tracks:
            self.draw_tracks(
                image,
                list(scene.tracks.values()),
                cfg.targets.tracks,
                camera_,
                *args,
            )
        if cfg.targets.switches:
            self.draw_switches(
                image,
                list(scene.switches.values()),
                cfg.targets.switches,
                *args,
            )

    def draw_tracks(
        self,
        image: npt.NDArray[np.uint8],
        tracks: list[target.ITrack],
        cfg: config.Tracks,
        camera_: camera.ICamera,
        *args: Union[target.TrackBedDrawOptions, target.RailDrawOptions],
    ) -> None:
        """
        Draw ITrack objects on image.
        :param image: Image to draw on
        :param tracks: ITrack objects to draw
        :param cfg: Configuration data class
        :param camera_: Image to world calculator
        :param args: Drawing attributes
        """
        track: target.ITrack
        if "drawing_order" in dir(cfg) and cfg.drawing_order is not None:
            for drawing_order_elem in cfg.drawing_order:
                for track in tracks:
                    if track.position == drawing_order_elem[0]:
                        self._track_drawer.draw(image, track, camera_, cfg, *args, drawing_element=drawing_order_elem[1])
        else:
            for track in tracks:
                self._track_drawer.draw(image, track, camera_, cfg, *args)

    def draw_switches(
        self,
        image: npt.NDArray[np.uint8],
        switches: list[target.ISwitch],
        cfg: config.Switches,
        aim_point: Optional[geometry.IImagePoint] = None,
        *args,
    ) -> None:
        """
        Draw ISwitch on image.
        :param image: Image to draw on
        :param switches: ISwitch object to draw
        :param cfg: Configuration data class
        :param aim_point: Where aime device points to
        :param args: Attributes of switch to draw
        """
        switch: target.ISwitch
        for switch in switches:
            self._switch_drawer.draw(image, switch, cfg, aim_point, *args)



class QtSceneDrawer(ISceneDrawer):
    """
    Draw scene using OpenCV.
    """

    def __init__(self) -> None:
        self._track_drawer: target.ITrackDrawer = target.track.drawer.QtTrackDrawer()
        self._switch_drawer: target.ISwitchDrawer = target.switch.draw.QtSwitchDrawer()

    def draw_scene(
        self,
        image: npt.NDArray[np.uint8],
        scene: IScene,
        cfg: config.Labels4RailsConfig,
        camera_: camera.ICamera,
        qt_scene,
        *args: Union[target.TrackBedDrawOptions, target.RailDrawOptions],
    ):
        """
        Draw IScene objects on an image.
        :param image: Image to draw on
        :param scene: IScene object
        :param cfg: Configuration data set
        :param camera_: Image to world calculator
        :param args: Drawing attributes
        :return: Image with IScene objects
        """
        if cfg.targets.tracks:
            self.draw_tracks(
                image,
                list(scene.tracks.values()),
                cfg.targets.tracks,
                camera_,
                qt_scene,
                *args,
            )
        if cfg.targets.switches:
            self.draw_switches(
                image,
                list(scene.switches.values()),
                cfg.targets.switches,
                qt_scene,
                *args,
            )

    def draw_tracks(
        self,
        image: npt.NDArray[np.uint8],
        tracks: list[target.ITrack],
        cfg: config.Tracks,
        camera_: camera.ICamera,
        qt_scene,
        *args: Union[target.TrackBedDrawOptions, target.RailDrawOptions],
    ) -> None:
        """
        Draw ITrack objects on image.
        :param image: Image to draw on
        :param tracks: ITrack objects to draw
        :param cfg: Configuration data class
        :param camera_: Image to world calculator
        :param args: Drawing attributes
        """
        track: target.ITrack
        if "drawing_order" in dir(cfg) and cfg.drawing_order is not None:
            for drawing_order_elem in cfg.drawing_order:
                for track in tracks:
                    if track.position == drawing_order_elem[0]:
                        self._track_drawer.draw(image, track, camera_, cfg, qt_scene, *args, drawing_element=drawing_order_elem[1])
        else:
            for track in tracks:
                self._track_drawer.draw(image, track, camera_, cfg, qt_scene, *args)

    def draw_switches(
        self,
        image: npt.NDArray[np.uint8],
        switches: list[target.ISwitch],
        cfg: config.Switches,
        qt_scene,
        aim_point: Optional[geometry.IImagePoint] = None,
        *args,
    ) -> None:
        """
        Draw ISwitch on image.
        :param image: Image to draw on
        :param switches: ISwitch object to draw
        :param cfg: Configuration data class
        :param aim_point: Where aime device points to
        :param args: Attributes of switch to draw
        """
        switch: target.ISwitch
        for switch in switches:
            self._switch_drawer.draw(image, switch, cfg, qt_scene, aim_point, *args)