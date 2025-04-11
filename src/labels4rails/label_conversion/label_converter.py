from typing import Optional
import abc
import pathlib
from labels4rails.utils import config
from labels4rails import data
from labels4rails import scene
from . import switch
from . import tracks


class ILabelConverter(metaclass=abc.ABCMeta):
    """
    Generate all labels on RailLabel scene.
    """

    @abc.abstractmethod
    def __init__(
        self,
        dataset: Optional[data.IDataSet] = None,
        cfg: Optional[config.Labels4RailsConfig] = None,
        path_to_chunk: Optional[str] = None,
    ) -> None:
        """
        Ether dataset or configuration is needed.
        :param dataset: Dataset describing scene
        :param cfg: RailLabel configuration
        """
        pass

    @abc.abstractmethod
    def generate_switch_labels(
        self,
        output_path: pathlib.Path,
        kinds: Optional[tuple[scene.target.SwitchKind]],
        directions: Optional[tuple[scene.target.SwitchDirection]],
    ) -> None:
        """
        Create labels for switches in given scene.
        :param output_path: Path to store labels
        :param kinds: List of desired switch kinds
        :param directions: List of desired directions
        """
        pass

    @abc.abstractmethod
    def generate_track_labels(
        self,
        output_path: pathlib.Path
    ) -> None:
        pass


class LabelConverterYOLO(ILabelConverter):
    """
    Generate YOLO labels provided by RailLabel dataset.
    """

    def __init__(
        self,
        dataset: Optional[data.IDataSet] = None,
        cfg: Optional[config.Labels4RailsConfig] = None,
        path_to_chunk: Optional[str] = None,
    ) -> None:
        """
        Ether dataset or configuration is needed.
        :param dataset: Dataset describing scene
        :param cfg: RailLabel configuration
        """
        if cfg is None and dataset is None:
            msg: str = "Expected ether configuration or dataset, got none of them."
            raise ValueError(msg)
        self._cfg: config.Labels4RailsConfig
        if cfg is not None:
            self._cfg = cfg
        else:
            ego_trackbed: config.Trackbed = config.TrackBed(255, [255,255,255], None, 15)
            ego_rail: config.Rail = config.Rail(255, None, None, None, [255,255,255], 15)
            ego_track: config.Track = config.Track(0,0,0,1, ego_trackbed, ego_rail, ego_rail)

            left_trackbed: config.Trackbed = config.TrackBed(85, [85,85,85], None, 15)
            left_rail: config.Rail = config.Rail(85, None, None, None, [85,85,85], 15)
            left_track: config.Track = config.Track(0,0,0,1, left_trackbed, left_rail, left_rail)

            right_trackbed: config.Trackbed = config.TrackBed(170, [170,170,170], None, 15)
            right_rail: config.Rail = config.Rail(170, None, None, None, [170,170,170], 15)
            right_track: config.Track = config.Track(0,0,0,1, right_trackbed, right_rail, right_rail)

            selected_trackbed: config.Trackbed = config.TrackBed(0, [0,0,0], None, 15)
            selected_rail: config.Rail = config.Rail(0, None, None, None, [0,0,0], 15)
            selected_track: config.Track = config.Track(0,0,0,1, selected_trackbed, selected_rail, selected_rail)

            drawing_order = (("left", "track_bed"),("left", "rails"),("right", "track_bed"),("right", "rails"),("ego","track_bed"),("ego", "rails"))

            tracks: config.Tracks = config.Tracks(ego_track, left_track, right_track, drawing_order, selected_track)
            targets: config.Targets = config.Targets(tracks, None, None)
            cfg_data: config.Data = config.Data(None, [], 1100, 67)
            included: config.Included = config.Included([None],[None],[None],[None],[None],[None])
            excluded: config.Excluded = config.Excluded([None],[None],[None],[None],[None],[None])
            self._cfg = config.Labels4RailsConfig(cfg_data, targets, None, 1, included, excluded)
        if path_to_chunk is not None:
            images = config.Images(str(pathlib.Path(path_to_chunk).joinpath("images")), ["jpg", "jpeg", "png"])
            self._cfg.data.paths = config.Paths(str(pathlib.Path(path_to_chunk).joinpath("camera").joinpath("camera.yaml")),
                                 images,
                                 str(pathlib.Path(path_to_chunk).joinpath("annotations")))
        if dataset is not None:
            self._dataset = dataset
        else:
            self._dataset: data.IDataSet = data.DataSet(self._cfg.data.paths)

    def generate_switch_labels(
        self,
        output_path: pathlib.Path,
        kinds: Optional[tuple[scene.target.SwitchKind]],
        directions: Optional[tuple[scene.target.SwitchDirection]],
    ) -> None:
        """
        Create bounding box labels in yolo format for switches in
        given scene.
        :param output_path: Path to store labels
        :param kinds: List of desired switch kinds
        :param directions: List of desired directions
        """
        kinds = tuple() if kinds is None else kinds
        directions = tuple() if directions is None else directions
        switch_label: switch.ISwitchLabel = switch.SwitchLabelConverterYOLO(self._dataset, self._cfg)
        switch_label(output_path, kinds, directions)

    def generate_track_labels(
        self,
        output_path: pathlib.Path
    ) -> None:
        pass

class LabelConverterPixelmask(ILabelConverter):
    """
    Generate all kind of labels provided by RailLabel dataset.
    """

    def __init__(
        self,
        dataset: Optional[data.IDataSet] = None,
        cfg: Optional[config.Labels4RailsConfig] = None,
        path_to_chunk: Optional[str] = None,
    ) -> None:
        """
        Ether dataset or configuration is needed.
        :param dataset: Dataset describing scene
        :param cfg: RailLabel configuration
        """
        if cfg is None and dataset is None and path_to_chunk is None:
            msg: str = "Expected ether configuration, dataset or path to data chunk, got none of them."
            raise ValueError(msg)
        if cfg is not None:
            ego_color = cfg.targets.tracks.ego.track_bed.export_mask_color
            cfg.targets.tracks.ego.track_bed.fill_color = [ego_color, ego_color, ego_color]
            ego_color_left_rail = cfg.targets.tracks.ego.left_rail.export_mask_color
            cfg.targets.tracks.ego.left_rail.fill_color = [ego_color_left_rail,ego_color_left_rail,ego_color_left_rail]
            ego_color_right_rail = cfg.targets.tracks.ego.right_rail.export_mask_color
            cfg.targets.tracks.ego.right_rail.fill_color = [ego_color_right_rail,ego_color_right_rail,ego_color_right_rail]

            left_color = cfg.targets.tracks.left.track_bed.export_mask_color
            cfg.targets.tracks.left.track_bed.fill_color = [left_color, left_color, left_color]
            left_color_left_rail = cfg.targets.tracks.left.left_rail.export_mask_color
            cfg.targets.tracks.left.left_rail.fill_color = [left_color_left_rail,left_color_left_rail,left_color_left_rail]
            left_color_right_rail = cfg.targets.tracks.left.right_rail.export_mask_color
            cfg.targets.tracks.left.right_rail.fill_color = [left_color_right_rail,left_color_right_rail,left_color_right_rail]
            
            right_color = cfg.targets.tracks.right.track_bed.export_mask_color
            cfg.targets.tracks.right.track_bed.fill_color = [right_color, right_color, right_color]
            right_color_left_rail = cfg.targets.tracks.right.left_rail.export_mask_color
            cfg.targets.tracks.right.left_rail.fill_color = [right_color_left_rail,right_color_left_rail,right_color_left_rail]
            right_color_right_rail = cfg.targets.tracks.right.right_rail.export_mask_color
            cfg.targets.tracks.right.right_rail.fill_color = [right_color_right_rail,right_color_right_rail,right_color_right_rail]

            self._cfg: config.Labels4RailsConfig = cfg
        else:
            ego_trackbed: config.Trackbed = config.TrackBed(255, [255,255,255], None, 15)
            ego_rail: config.Rail = config.Rail(255, None, None, None, [255,255,255], 15)
            ego_track: config.Track = config.Track(0,0,0,1, ego_trackbed, ego_rail, ego_rail)

            left_trackbed: config.Trackbed = config.TrackBed(85, [85,85,85], None, 15)
            left_rail: config.Rail = config.Rail(85, None, None, None, [85,85,85], 15)
            left_track: config.Track = config.Track(0,0,0,1, left_trackbed, left_rail, left_rail)

            right_trackbed: config.Trackbed = config.TrackBed(170, [170,170,170], None, 15)
            right_rail: config.Rail = config.Rail(170, None, None, None, [170,170,170], 15)
            right_track: config.Track = config.Track(0,0,0,1, right_trackbed, right_rail, right_rail)

            selected_trackbed: config.Trackbed = config.TrackBed(0, [0,0,0], None, 15)
            selected_rail: config.Rail = config.Rail(0, None, None, None, [0,0,0], 15)
            selected_track: config.Track = config.Track(0,0,0,1, selected_trackbed, selected_rail, selected_rail)

            drawing_order = (("left", "track_bed"),("left", "rails"),("right", "track_bed"),("right", "rails"),("ego","track_bed"),("ego", "rails"))

            tracks: config.Tracks = config.Tracks(ego_track, left_track, right_track, drawing_order, selected_track)
            targets: config.Targets = config.Targets(tracks, None, None)
            cfg_data: config.Data = config.Data(None, [], 1100, 67)
            included: config.Included = config.Included([None],[None],[None],[None],[None],[None])
            excluded: config.Excluded = config.Excluded([None],[None],[None],[None],[None],[None])
            self._cfg: config.Labels4RailsConfig = config.Labels4RailsConfig(cfg_data, targets, None, None,included, excluded)
        if path_to_chunk is not None:
            images = config.Images(str(pathlib.Path(path_to_chunk).joinpath("images")), ["jpg", "jpeg", "png"])
            self._cfg.data.paths = config.Paths(str(pathlib.Path(path_to_chunk).joinpath("camera").joinpath("camera.yaml")),
                                 images,
                                 str(pathlib.Path(path_to_chunk).joinpath("annotations")))

        if dataset is not None:
            self._dataset = dataset
        else:
            self._dataset: data.IDataSet = data.DataSet(self._cfg.data.paths)

    def generate_switch_labels(
        self,
        output_path: pathlib.Path,
        kinds: Optional[tuple[scene.target.SwitchKind]],
        directions: Optional[tuple[scene.target.SwitchDirection]],
    ) -> None:
        pass

    def generate_track_labels(
        self,
        output_path: pathlib.Path
    ) -> None:
        track_label: tracks.ITrackLabelConverter 
        track_label = tracks.TrackLabelConverterPixelmask(self._dataset, self._cfg)
        track_label(output_path)