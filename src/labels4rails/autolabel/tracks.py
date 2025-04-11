from PyQt5.QtWidgets import QMessageBox

from labels4rails import data
from labels4rails import gui
from labels4rails import utils
from labels4rails.annotate.qt_annotator import QtAnnotator
from labels4rails.utils import config


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
        self._gui_event.subscribe(gui.GuiEvents.SEMI_AUTO_LABELING_TRACK, self.semi_auto_detect)

    def __del__(self):
        self._gui_event.unsubscribe_all(self.auto_detect)
        self._gui_event.unsubscribe_all(self.semi_auto_detect)

    def auto_detect(self):
        print("This is the auto labeling mode (Track)! Please ignore me!")

    def semi_auto_detect(self):
        print("This is the semi auto labeling mode (Track)! Please ignore me!")