import os
import math
import torch
from PIL import Image

from labels4rails import data
from labels4rails import gui
from labels4rails import utils
from labels4rails.scene import target as sceneTarget
from labels4rails.annotate.qt_annotator import QtAnnotator
from labels4rails.utils import config
from labels4rails.autolabel.models.tracks.utils.interface import Detector


class AutoTracks:
    def __init__(
            self,
            annotator: QtAnnotator = None,
            cfg: config.Labels4RailsConfig = None,
            dataset: data.DataSet = None,
            gui_event: utils.IEventHub = None
    ) -> None:
        self._annotator = annotator
        self._cfg = cfg
        self._dataset = dataset
        self._gui_event = gui_event

        # Subscriptions
        self._gui_event.subscribe(gui.GuiEvents.AUTO_LABELING_TRACK, self.auto_detect)

    def __del__(self):
        self._gui_event.unsubscribe_all(self.auto_detect)

    """
    Ramer-Douglas-Peucker (RDP) algorithm to reduce keypoints on a given track
    """
    def _point_line_distance(self, point, start, end):
        if start == end:
            return math.dist(point, start)

        x, y = point
        x1, y1 = start
        x2, y2 = end

        numerator = abs((y2 - y1)*x - (x2 - x1)*y + x2*y1 - y2*x1)
        denominator = math.hypot(y2 - y1, x2 - x1)

        return numerator / denominator

    def _rdp(self, points, epsilon):
        if len(points) < 3:
            return points

        start, end = points[0], points[-1]
        max_dist = 0.0
        index = 0

        for i in range(1, len(points) - 1):
            dist = self._point_line_distance(points[i], start, end)

            if dist > max_dist:
                index = i
                max_dist = dist

        if max_dist > epsilon:
            first_half = self._rdp(points[:index+1], epsilon)
            second_half = self._rdp(points[index:], epsilon)
            return first_half[:-1] + second_half
        else:
            return [start, end]

    """
    The classes entry point / main method. Handles the detection and GUI handling of auto tracks.
    """
    def auto_detect(self):
        scene = self._annotator.get_scene()
        scene_index = self._annotator.get_datacounter()
        scene_image = self._dataset[scene_index].image

        results = []
        tracks = scene.tracks
        track_ids = list(tracks.keys())

        image = Image.fromarray(scene_image)
        base_path = os.path.dirname(__file__)
        device = "cpu"

        # Detect ego track
        if torch.cuda.is_available():
            device = "cuda"

        detector = Detector(
            model_path=os.path.join(base_path, "models/tracks/weights", "logical-tree-1"),
            crop_coords="auto",
            device=device
        )

        for iteration in range(50):
            detector.get_crop_coords()
            results = detector.detect(image)

        # Remove previous ego track
        for track in list(tracks.values()):
            if track.position == "ego":
                scene.del_track(track.id)

        # Add detected ego track (Simplify using RDP)
        detected_ego_track = scene.add_track(sceneTarget.TrackPosition.EGO, 67)

        epsilon = 1.0
        simplified_left = self._rdp(results[0], epsilon)
        simplified_right = self._rdp(results[1], epsilon)

        for x, y in simplified_left:
            pos = utils.geometry.ImagePoint(x, y)
            scene.tracks[detected_ego_track.id].left_rail.add_mark(pos)

        for x, y in simplified_right:
            pos = utils.geometry.ImagePoint(x, y)
            scene.tracks[detected_ego_track.id].right_rail.add_mark(pos)

        if results:
            scene.tracks[detected_ego_track.id].position = "ego"
            self._gui_event.post(gui.GuiEvents.TRACK_LIST_UPDATE, tracks.values(), -1)
            self._gui_event.post(gui.GuiEvents.DISPLAY)
            self._annotator.update_annotations()