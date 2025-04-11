from typing import Union, Optional
import abc
import dataclasses
import json
import pathlib
from natsort import natsorted, ns
from labels4rails.utils import config
import numpy as np
import numpy.typing as npt
import cv2
from . import camera_config
from labels4rails.utils.config import Labels4RailsConfig


# replaced by qt filedialoge
 
'''
cv2.imread in __get_item__
self._camera_reader = camera_config.OpenCVCameraReader
'''


@dataclasses.dataclass
class Data:
    """
    Data describing one scene
    """

    image: npt.NDArray[np.uint8]
    name: str
    annotation: dict
    camera_cfg: camera_config.ICameraReader


class IDataSet(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __init__(self, cfg: config.Paths, dataset_path: Optional[str] = None) -> None:
        """
        Initialize the data loader.
        :param cfg: Configuration data class
        """

    @abc.abstractmethod
    def __len__(self) -> int:
        pass

    @abc.abstractmethod
    def __getitem__(self, item) -> Data:
        pass

    def write_annotations(self, annotations, item, cfg) -> None:
        """
        Write serialized scenes to dedicated JSON file.
        :param annotations: Serialized scene to write
        """
        pass


class DataSet(IDataSet):
    """
    Loads images and annotations.
    """

    def __init__(self, cfg: config.Paths, dataset_path: Optional[str] = None) -> None:
        """
        Initialize the data loader.
        :param cfg: Configuration data class
        """
        if cfg:
            images_path: Union[pathlib.Path, str]
            images_path = pathlib.Path(cfg.images.path)
            print(images_path)
            if not images_path.is_dir():
                msg: str = "Expected 'images_path' to be a directory."
                raise NotADirectoryError(msg)
            extensions = set(cfg.images.extensions)
            self._images_paths = []
            for extension in extensions:
                for image_path in images_path.glob(f"*.{extension}"):
                    self._images_paths.append(image_path)
            self._images_paths = natsorted(self._images_paths, alg=ns.IGNORECASE)

            self._annotations_path: Union[pathlib.Path, str]
            self._annotations_path = pathlib.Path(cfg.annotations)
            self._annotations_path.mkdir(parents=True, exist_ok=True)
            self._annotation_path: Optional[pathlib.Path] = None

            camera_config_path: Union[pathlib.Path, str]
            camera_config_path = pathlib.Path(cfg.camera_extrinsic)

            self._camera_reader = camera_config.OpenCVCameraReader(camera_config_path)
        elif dataset_path:
            images_path: Union[pathlib.Path, str]
            images_path = pathlib.Path(dataset_path).joinpath("images")
            if not images_path.is_dir():
                msg: str = "Expected 'images_path' to be a directory."
                raise NotADirectoryError(msg)
            extensions: set = {"jpg", "jepg", "png"}
            self._images_paths = []
            for extension in extensions:
                for image_path in images_path.glob(f"*.{extension}"):
                    self._images_paths.append(image_path)
            self._images_paths = sorted(self._images_paths)

            self._annotations_path: Union[pathlib.Path, str]
            self._annotations_path = pathlib.Path(dataset_path).joinpath("annotations")
            self._annotations_path.mkdir(parents=True, exist_ok=True)
            self._annotation_path: Optional[pathlib.Path] = None

            camera_config_path: Union[pathlib.Path, str]
            camera_config_path = pathlib.Path(dataset_path).joinpath("camera/camera.yaml")

            self._camera_reader = camera_config.OpenCVCameraReader(camera_config_path)
        else:
            raise ValueError("No dataset.")

    def __len__(self) -> int:
        return len(self._images_paths)

    def __getitem__(self, item) -> Data:
        image_path = self._images_paths[item]
        image = cv2.imread(str(image_path))
        # Try to get annotations file.
        annotation_path = self._annotations_path / (image_path.stem + ".json")
        try:
            with open(annotation_path) as file_pointer:
                annotation = json.load(file_pointer)
        except FileNotFoundError:
            annotation = None
        data = Data(image, image_path.stem, annotation, self._camera_reader)
        return data

    def write_annotations(self, annotations, item, cfg: Labels4RailsConfig) -> None:
        """
        Write serialized scenes to dedicated JSON file.
        :param annotations: Serialized scene to write
        """
        image_path = self._images_paths[item]
        annotation_path = self._annotations_path / (image_path.stem + ".json")
        annotations = self.__check_unknown_tags(annotations, annotation_path, cfg)
        with open(annotation_path, "w") as file_pointer:
            json.dump(annotations, file_pointer, indent=4, sort_keys=True)

    def __check_unknown_tags(self, annotations, annotation_path, cfg: Labels4RailsConfig):
        """
        Method that checks if annotation has any unknown tags that are not specified in the config.
        Any unknown tags will be added to the annotations dictionary
        :param annotations: annotation that is supposed to get saved
        :param annotation_path: path to the annotation
        :param cfg: config file with the target tags

        """

        cfg_tags = dict(cfg.targets.tags)
        """
        config.yaml defines additional as tag group however the annotations define them as additional_attributes
        The line below can be removed if the config tag group additional gets renamed

        """
        cfg_tags["additional_attributes"] = cfg_tags.pop("additional")

        cfg_group = list(cfg_tags.keys())
        if pathlib.Path(annotation_path).is_file():
            with open(annotation_path, "r") as file:
                data = json.load(file)
                if "tag groups" in data:
                    data = data["tag groups"]
                    if data == annotations["tag groups"]:
                        return annotations
                    else:
                        file_group = list(data.keys())
                        difference_groups = list(set(file_group) - set(cfg_group))
                        if len(difference_groups) != 0:
                            for additionalGroups in difference_groups:
                                annotations["tag groups"][additionalGroups] = data[additionalGroups]
                        if data == annotations["tag groups"]:
                            return annotations

                        for group, tags in data.items():
                            if group not in difference_groups:
                                difference_tags = list(set(tags) - set(cfg_tags[group]))
                                if len(difference_tags) != 0:
                                    for unknown_tag in difference_tags:
                                        if unknown_tag not in annotations["tag groups"][group]:
                                            annotations["tag groups"][group] = annotations["tag groups"][group] + [unknown_tag]



                return annotations


        else:
            return annotations
