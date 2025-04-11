from typing import Optional
import abc
from labels4rails import data
import pathlib
from labels4rails import scene
from labels4rails import utils
from labels4rails.utils import config
import numpy as np
from ..TagFilter import TagFilter
import cv2

class ITrackLabelConverter(metaclass=abc.ABCMeta):
    """
    Generate labels for track.
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
        track_position: Optional[list[scene.target.TrackPosition]] = None,
        separate_rails: Optional[bool] = True, 
    ) -> None:
        """
        Store pixelmasks in given path. The pixelmasks contain the . If either 'kind' or 'direction' is
        empty this attribute is considered as not interesting. Being both empty
        is invalid. That means if the switch is selected by the other attribute
        class ids get grouped. E.g. if directions list ist empty and merges are
        selected in the kinds list all merges will get the same class id.
        :param output_path: Path to store labels
        :param track_position: List of desired track positions
        """
        pass

class TrackLabelConverterPixelmask(ITrackLabelConverter):
    """
    Generate Pixelmasks for Tracks.
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
        self._cfg = cfg
        self._scene_deserializer: scene.ISceneSerializer
        self._scene_deserializer = scene.DictSceneSerializer()

    def __call__(
        self,
        output_path: pathlib.Path,
        track_position: Optional[list[scene.target.TrackPosition]] = None,
        separate_rails: Optional[bool] = True, 
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
        :param track_position: List of desired track positions
        """
        track_position = () if track_position is None else track_position

        data_: data.Data
        scene_drawer_: scene.ISceneDrawer = scene.OpenCVSceneDrawer()
        camera_: utils.camera.ICamera = utils.camera.Camera(self._dataset[0].camera_cfg)

        cfg_: config.Labels4RailsConfig = self._cfg
        draw_options_: list[
            Union[
                scene.target.RailDrawOptions,
                scene.target.TrackBedDrawOptions,
            ]
        ]
        draw_options_ = [
            scene.target.RailDrawOptions.FILL,
            scene.target.TrackBedDrawOptions.FILL,
        ]
        filtered_list = TagFilter(self._dataset._annotations_path, self._cfg).annotationList

        for data_ in self._dataset:
            if data_.name in filtered_list:
                scene_: scene.IScene
                if data_.annotation:
                    scene_ = self._scene_deserializer.de_serialize(data_.annotation)
                    resolution: tuple[int, int] = data_.image.shape[:2]
                    image = np.zeros((resolution[0], resolution[1]), dtype = np.uint8)
                    scene_drawer_.draw_scene(image, scene_, cfg_, camera_, *draw_options_)

                    mask_path = output_path.joinpath(data_.name + ".png")
                    cv2.imwrite(str(mask_path), image)
                else:
                    print("No mask created for", data_.name, ". No corresponding annotation file found.")
