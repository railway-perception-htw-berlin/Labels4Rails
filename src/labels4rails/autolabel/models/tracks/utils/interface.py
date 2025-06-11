import os
import torch
import yaml
import numpy as np

from PIL import Image
from torchvision.transforms import v2 as transforms

from ..nn.model import ClassificationNet, RegressionNet, SegmentationNet
from .autocrop import Autocropper
from .postprocessing import (classifications_to_rails, regression_to_rails, scale_mask, scale_rails)


class Detector:
    def __init__(self, model_path, crop_coords, device):
        self.model_path = model_path
        self.device = torch.device(device)

        with open(os.path.join(self.model_path, "config.yaml")) as f:
            self.config = yaml.safe_load(f)

        if isinstance(crop_coords, tuple) and len(crop_coords) == 4:
            self.crop_coords = crop_coords
        elif crop_coords == "auto":
            self.crop_coords = Autocropper(self.config)
        else:
            self.crop_coords = None

        self.model = self.init_model_pytorch()

    def get_crop_coords(self):
        return (
            self.crop_coords()
            if isinstance(self.crop_coords, Autocropper)
            else self.crop_coords
        )

    def preprocess_image(self, img):
        transform = transforms.Compose([
            transforms.ToImage(),
            transforms.ToDtype(torch.float32, scale=True)
        ])

        return transform(img).unsqueeze(0).to(self.device)

    def init_model_pytorch(self):
        if self.config["method"] == "classification":
            model = ClassificationNet(
                backbone=self.config["backbone"],
                input_shape=tuple(self.config["input_shape"]),
                anchors=self.config["anchors"],
                classes=self.config["classes"],
                pool_channels=self.config["pool_channels"],
                fc_hidden_size=self.config["fc_hidden_size"],
            )
        elif self.config["method"] == "regression":
            model = RegressionNet(
                backbone=self.config["backbone"],
                input_shape=tuple(self.config["input_shape"]),
                anchors=self.config["anchors"],
                pool_channels=self.config["pool_channels"],
                fc_hidden_size=self.config["fc_hidden_size"],
            )
        elif self.config["method"] == "segmentation":
            model = SegmentationNet(
                backbone=self.config["backbone"],
                decoder_channels=tuple(self.config["decoder_channels"]),
            )

        model.to(self.device).eval()
        model.load_state_dict(
            torch.load(
                os.path.join(self.model_path, "best.pt"), map_location=self.device
            )
        )

        return model

    def infer_model_pytorch(self, img):
        tensor = self.preprocess_image(img)
        tensor = transforms.Resize(self.config["input_shape"][1:][::-1])(tensor)

        with torch.inference_mode():
            pred = self.model(tensor)

        return pred.cpu().numpy()

    def detect(self, img):
        original_shape = img.size
        crop_coords = self.get_crop_coords()

        if crop_coords is not None:
            xleft, ytop, xright, ybottom = crop_coords
            img = img.crop((xleft, ytop, xright + 1, ybottom + 1))

        pred = self.infer_model_pytorch(img)

        if self.config["method"] == "classification":
            clf = pred.reshape(2, self.config["anchors"], self.config["classes"] + 1)
            clf = np.argmax(clf, axis=2)
            rails = classifications_to_rails(clf, self.config["classes"])
            rails = scale_rails(rails, crop_coords, original_shape)
            rails = np.round(rails).astype(int)
            res = rails.tolist()
        elif self.config["method"] == "regression":
            traj = pred[:, :-1].reshape(2, self.config["anchors"])
            ylim = 1 / (1 + np.exp(-pred[:, -1].item()))
            rails = regression_to_rails(traj, ylim)
            rails = scale_rails(rails, crop_coords, original_shape)
            rails = np.round(rails).astype(int)
            res = rails.tolist()
        elif self.config["method"] == "segmentation":
            mask = pred.squeeze(0).squeeze(0)
            mask = (mask > 0).astype(np.uint8) * 255
            mask = Image.fromarray(mask)
            res = scale_mask(mask, crop_coords, original_shape)

        if isinstance(self.crop_coords, Autocropper):
            self.crop_coords.update(original_shape, res)

        return res
