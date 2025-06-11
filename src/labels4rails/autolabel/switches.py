import cv2
import numpy as np

from PyQt5.QtWidgets import QMessageBox

from labels4rails import data
from labels4rails import gui
from labels4rails import utils
from labels4rails.annotate.qt_annotator import QtAnnotator
from labels4rails.utils import config
from labels4rails.scene import target

class AutoSwitches:
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
        self._gui_event.subscribe(gui.GuiEvents.AUTO_LABELING_SWITCH, self.auto_detect)

    def __del__(self):
        self._gui_event.unsubscribe_all(self.auto_detect)

    """
    Get the rail points of a track as a dictionary.
    """
    def _get_rail_points(self, track):
        left = np.array([[p.point[0], p.point[1]] for p in track.left_rail.marks], dtype=np.int32)
        right = np.array([[p.point[0], p.point[1]] for p in track.right_rail.marks], dtype=np.int32)
        return {"left": left, "right": right}

    """
    Creates a mask for a track based on its rail points.
    """
    def _create_track_mask(self, track, resolution):
        mask = np.zeros((resolution[0], resolution[1]), dtype=np.uint8)
        rail_points = self._get_rail_points(track)

        if len(rail_points["left"]) == 0 or len(rail_points["right"]) == 0:
            return mask

        track_points = np.vstack((rail_points["left"], rail_points["right"][::-1]))
        track_points = np.clip(track_points, 0, [resolution[1]-1, resolution[0]-1])
        cv2.fillPoly(mask, [track_points], 255)

        return mask

    """
    Creates a bounding box based on the overlapping areas of the two track masks.
    """
    def _create_bounding_box_native(self, mask1, mask2):
        overlap = cv2.bitwise_and(mask1, mask2)

        if not np.any(overlap):
            return None

        y_indices, x_indices = np.where(overlap > 0)
        x_min, x_max = np.min(x_indices), np.max(x_indices)
        y_min, y_max = np.min(y_indices), np.max(y_indices)

        return [int(x_min), int(y_min), int(x_max), int(y_max)]

    """
    Creates a bounding box which reaches beyond the switches point blade.
    """
    def _create_bounding_box_expanded(self, mask1, mask2, type, direction):
        bounding_box_native = self._create_bounding_box_native(mask1, mask2)
        bounding_box_expanded = list(bounding_box_native)
        scanline = 0

        if type == "unknown" or direction == "unknown":
            return bounding_box_native

        if type == "fork":
            scanline = min(bounding_box_native[3] + 1, mask1.shape[0] - 1)
        elif type == "merge":
            scanline = max(bounding_box_native[1] - 1, 0)

        mask1_row = mask1[scanline, :]
        mask2_row = mask2[scanline, :]
        mask1_positive = np.where(mask1_row > 0)[0]
        mask2_positive = np.where(mask2_row > 0)[0]

        left_edge_m1 = np.min(mask1_positive) if mask1_positive.size else bounding_box_native[0]
        left_edge_m2 = np.min(mask2_positive) if mask2_positive.size else bounding_box_native[0]
        right_edge_m1 = np.max(mask1_positive) if mask1_positive.size else bounding_box_native[2]
        right_edge_m2 = np.max(mask2_positive) if mask2_positive.size else bounding_box_native[2]

        if direction == "left":
            bounding_box_expanded[0] = min(left_edge_m1, left_edge_m2)
        elif direction == "right":
            bounding_box_expanded[2] = max(right_edge_m1, right_edge_m2)

        return bounding_box_expanded

    """
    Determines whether a track (or more precise its mask) is present at a given scanline position.
    """
    def _get_track_existence_at_scanline(self, mask, scanline_pos):
        return int(np.any(mask[scanline_pos]))

    """
    Determines the type of the switch based on the amount of tracks above and below the provided bounding box.
    """
    def _get_switch_type(self, mask1, mask2, bounding_box):
        type = None

        bb_above_pos = max(bounding_box[1] - 1, 1) # Take scanline above and below bounding-box, take last available scanline when at image border
        bb_below_pos = min(bounding_box[3] + 1, mask1.shape[0] - 1)

        above_track_amount = self._get_track_existence_at_scanline(mask1, bb_above_pos) + self._get_track_existence_at_scanline(mask2, bb_above_pos)
        below_track_amount = self._get_track_existence_at_scanline(mask1, bb_below_pos) + self._get_track_existence_at_scanline(mask2, bb_below_pos)

        if above_track_amount < below_track_amount:
            type = "merge"
        elif above_track_amount > below_track_amount:
            type = "fork"
        else:
            type = "unknown"

        return type

    """
    Get the innermost Y-edge of a given track.
    Truncate for merge/fork switches at the top or bottom of the bounding box respectively.
    """
    def _get_track_edges_point_center(self, rail_points, clip_pos, compare_func, extreme_func):
        left_points = rail_points["left"][compare_func(rail_points["left"][:, 1], clip_pos)]
        right_points = rail_points["right"][compare_func(rail_points["right"][:, 1], clip_pos)]

        left_x = left_points[extreme_func(left_points[:, 1])][0]
        right_x = right_points[extreme_func(right_points[:, 1])][0]
        return np.array([(left_x + right_x) / 2, clip_pos])

    """
    Get the outermost Y-edge of a given track.
    """
    def _get_track_edges_point_border(self, rail_points, extreme_func):
        left_point = rail_points["left"][extreme_func(rail_points["left"][:, 1])]
        right_point = rail_points["right"][extreme_func(rail_points["right"][:, 1])]
        return (left_point + right_point) / 2

    """
    For tracks involved in merge switches:
    Get the left/right coordinates of both the bottom and top edges of the given track.
    """
    def _get_track_edges_merge(self, clip_pos, track):
        rail_points = self._get_rail_points(track)
        edge_bottom = self._get_track_edges_point_border(rail_points, np.argmax)
        edge_top = self._get_track_edges_point_center(rail_points, clip_pos, np.greater_equal, np.argmin)
        return [edge_bottom, edge_top]

    """
    For tracks involved in fork switches:
    Get the left/right coordinates of both the bottom and top edges of the given track.
    """
    def _get_track_edges_fork(self, clip_pos, track):
        rail_points = self._get_rail_points(track)
        edge_bottom = self._get_track_edges_point_center(rail_points, clip_pos, np.less_equal, np.argmax)
        edge_top = self._get_track_edges_point_border(rail_points, np.argmin)
        return [edge_bottom, edge_top]

    """
    Determine whether track1 is to the left or to the right respective to track2.
    Next, determine which of both tracks should be regarded as the point of reference (reference_track).
    Next, declare the switch direction based on the position of the reference_track relative to the other track.
    """
    def _get_switch_direction(self, track1, track2, mask1, mask2, bounding_box, type):
        left_track = None
        right_track = None
        reference_track = None
        result = None

        # Direction not determinable for unknown switches
        if type == "unknown":
            return "unknown"

        # Assign direction of tracks based on switch-type and track x-coordinates
        if type == "merge":
            edges_track1 = self._get_track_edges_merge(bounding_box[1], track1)
            edges_track2 = self._get_track_edges_merge(bounding_box[1], track2)
            left_track = track1 if edges_track1[0][0] < edges_track2[0][0] else track2
            right_track = track2 if edges_track1[0][0] < edges_track2[0][0] else track1
        elif type == "fork":
            edges_track1 = self._get_track_edges_fork(bounding_box[3], track1)
            edges_track2 = self._get_track_edges_fork(bounding_box[3], track2)
            left_track = track1 if edges_track1[1][0] < edges_track2[1][0] else track2
            right_track = track2 if edges_track1[1][0] < edges_track2[1][0] else track1

        # Count how often both tracks appear above and below the bounding box
        bb_above_pos = max(bounding_box[1] - 1, 1)
        bb_below_pos = min(bounding_box[3] + 1, mask1.shape[0] - 1)
        track1_amount = self._get_track_existence_at_scanline(mask1, bb_above_pos) + self._get_track_existence_at_scanline(mask1, bb_below_pos)
        track2_amount = self._get_track_existence_at_scanline(mask2, bb_above_pos) + self._get_track_existence_at_scanline(mask2, bb_below_pos)

        # The track which appears more often is declared the reference track
        if track1_amount > track2_amount:
            reference_track = track1
        elif track1_amount < track2_amount:
            reference_track = track2

        # Determine the direction of the main track
        if reference_track == left_track:
            result = "left"
        elif reference_track == right_track:
            result = "right"
        else:
            result = "unknown"

        return result

    """
    The classes entry point / main method. Handles the detection and GUI handling of auto switches.
    """
    def auto_detect(self):
        scene = self._annotator.get_scene()
        scene_index = self._annotator.get_datacounter()
        scene_resolution = self._dataset[scene_index].image.shape[:2]

        results = []
        tracks = scene.tracks
        track_ids = list(tracks.keys())

        # Detect all switches
        for i in range(len(track_ids)):
            for j in range(i + 1, len(track_ids)):
                id1, id2 = track_ids[i], track_ids[j]

                mask1 = self._create_track_mask(tracks[id1], scene_resolution)
                mask2 = self._create_track_mask(tracks[id2], scene_resolution)
                bounding_box_native = self._create_bounding_box_native(mask1, mask2)

                if bounding_box_native:
                    type = self._get_switch_type(mask1, mask2, bounding_box_native)
                    direction = self._get_switch_direction(tracks[id1], tracks[id2], mask1, mask2, bounding_box_native, type)
                    bounding_box_expanded = self._create_bounding_box_expanded(mask1, mask2, type, direction)

                    results.append({
                        "track_ids": (id1, id2),
                        "bounding_box": bounding_box_expanded,
                        "type": type,
                        "direction": direction
                    })

        # Handle detected switches in GUI
        for result in results:
            if result["type"] == "merge":
                if result["direction"] == "left":
                    scene.add_switch(
                        target.SwitchKind.MERGE,
                        target.SwitchDirection.LEFT,
                    )
                elif result["direction"] == "right":
                    scene.add_switch(
                        target.SwitchKind.MERGE,
                        target.SwitchDirection.RIGHT,
                    )
                elif result["direction"] == "unknown":
                    scene.add_switch(
                        target.SwitchKind.MERGE,
                        target.SwitchDirection.UNKNOWN,
                    )
            elif result["type"] == "fork":
                if result["direction"] == "left":
                    scene.add_switch(
                        target.SwitchKind.FORK,
                        target.SwitchDirection.LEFT,
                    )
                elif result["direction"] == "right":
                    scene.add_switch(
                        target.SwitchKind.FORK,
                        target.SwitchDirection.RIGHT,
                    )
                elif result["direction"] == "unknown":
                    scene.add_switch(
                        target.SwitchKind.FORK,
                        target.SwitchDirection.UNKNOWN,
                    )
            elif result["type"] == "unknown":
                scene.add_switch(
                    target.SwitchKind.UNKNOWN,
                    target.SwitchDirection.UNKNOWN,
                )

            switches = scene.switches
            switch_ids = list(switches.keys())

            switches[switch_ids[-1]].add_track_ids(list(result["track_ids"]))

            bounding_box = result["bounding_box"]
            bounding_box_pos = [
                utils.geometry.ImagePoint(bounding_box[0], bounding_box[1]),
                utils.geometry.ImagePoint(bounding_box[2], bounding_box[3])
            ]

            for bb_corner in bounding_box_pos:
                switches[switch_ids[-1]].add_mark([bb_corner])

        if results:
            self._gui_event.post(gui.GuiEvents.SWITCH_LIST_UPDATE, switches.values())
            self._gui_event.post(gui.GuiEvents.DISPLAY)
            self._annotator.update_annotations()
