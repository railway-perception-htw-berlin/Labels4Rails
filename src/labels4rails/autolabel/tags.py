import clip
import numpy as np
import torch
from PIL import Image

from labels4rails import data
from labels4rails import gui
from labels4rails import utils
from labels4rails.annotate.qt_annotator import QtAnnotator
from labels4rails.utils import config


class AutoTags:
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

        # Initialize CLIP model (downloading model to "~/.cache/clip")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.preprocess = clip.load("ViT-B/16", device=self.device)

        # Subscriptions
        self._gui_event.subscribe(gui.GuiEvents.AUTO_LABELING_TAG, self.auto_detect)

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
    Determines whether a track is straight or curved.
    """
    def _get_tag_track_layout(self, track):
        track_rail = self._get_rail_points(track)["left"]
        if len(track_rail) > 0:
            track_rail = track_rail[track_rail[:, 1].argsort()]
            point_upper = track_rail[0]
            point_lower = track_rail[-1]

            slope = (point_lower[1] - point_upper[1]) / (point_lower[0] - point_upper[0])
            intercept = point_upper[1] - slope * point_upper[0]

            distance = np.abs(slope * track_rail[:, 0] + -1 * track_rail[:, 1] + intercept) / np.sqrt(slope**2 + -1**2)
            rmse = np.sqrt(np.mean(distance**2))

            if rmse < 5:
                return "straight"
            else:
                return "curve"

    """
    Utilizing CLIP to determine the best matching tag for a given category.
    """
    def _get_tag_clip(self, image):
        tags = {}
        tag_categories = {
            "weather": self._cfg.targets.tags.weather,
            "light": self._cfg.targets.tags.light,
            "time_of_day": self._cfg.targets.tags.time_of_day,
            "environment": self._cfg.targets.tags.environment
        }
        image_input = self.preprocess(image).unsqueeze(0).to(self.device)

        for category, options in tag_categories.items():
            # Filter out "unknown" and "auto"
            valid_options = [tag for tag in options if tag not in ["unknown", "auto"]]

            if not valid_options:
                tags[category] = "unknown"
                continue

            # Create prompts for CLIP
            if category == "weather":
                text_prompts = [f"A railway scene with {tag} weather" for tag in valid_options]
            elif category == "light":
                text_prompts = [f"A railway scene with {tag} lighting" for tag in valid_options]
            elif category == "time_of_day":
                text_prompts = [f"A railway scene during {tag}" for tag in valid_options]
            elif category == "environment":
                text_prompts = [f"A railway scene in {tag} environment" for tag in valid_options]
            else:
                text_prompts = [f"A railway scene with {tag}" for tag in valid_options]

            # Tokenize, encode and select result
            text_inputs = clip.tokenize(text_prompts).to(self.device)

            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                text_features = self.model.encode_text(text_inputs)

                similarities = torch.cosine_similarity(image_features, text_features)
                best_idx = similarities.argmax().item()
                confidence = similarities[best_idx].item()

                if confidence > 0.15:
                    tags[category] = valid_options[best_idx]
                else:
                    tags[category] = "unknown"

        return tags

    """
    The classes entry point / main method.
    """
    def auto_detect(self):
        scene = self._annotator.get_scene()
        scene_index = self._annotator.get_datacounter()
        scene_image = self._dataset[scene_index].image

        tracks = scene.tracks

        # Reset all present tags and set only "auto"
        scene.tag_groups.track_layout = ["auto"]
        scene.tag_groups.weather = ["auto"]
        scene.tag_groups.light = ["auto"]
        scene.tag_groups.time_of_day = ["auto"]
        scene.tag_groups.environment = ["auto"]

        # Classical detection for "track_layout"
        for track in tracks.values():
            result_track_layout = self._get_tag_track_layout(track)
            
            if result_track_layout and result_track_layout not in scene.tag_groups.track_layout:
                scene.tag_groups.track_layout.append(result_track_layout)

        # CLIP-based detection for other tag groups
        result_clip = self._get_tag_clip(Image.fromarray(scene_image))
        
        if result_clip["weather"] not in scene.tag_groups.weather:
            scene.tag_groups.weather.append(result_clip["weather"])
        if result_clip["light"] not in scene.tag_groups.light:
            scene.tag_groups.light.append(result_clip["light"])
        if result_clip["time_of_day"] not in scene.tag_groups.time_of_day:
            scene.tag_groups.time_of_day.append(result_clip["time_of_day"])
        if result_clip["environment"] not in scene.tag_groups.environment:
            scene.tag_groups.environment.append(result_clip["environment"])

        # Update GUI
        self._gui_event.post(
            gui.GuiEvents.TAG_ALL_LISTS_UPDATE,
            {
                "track_layout": scene.tag_groups.track_layout,
                "weather": scene.tag_groups.weather,
                "light": scene.tag_groups.light,
                "time_of_day": scene.tag_groups.time_of_day,
                "environment": scene.tag_groups.environment,
                "additional": scene.tag_groups.additional_attributes
            }
        )