import sys
import os
import traceback

from re import findall
from natsort import natsorted, ns

from .gui_init import Ui_MainWindow
from .flow import FlowLayout

from PyQt5 import (QtCore, QtWidgets)
from PyQt5.QtCore import (QRect, QPoint, pyqtSignal, QEvent)
from PyQt5.QtWidgets import (QFileDialog, QWidget, QDockWidget, QMessageBox, QScrollArea)
from PyQt5.QtGui import QResizeEvent

from labels4rails import data
from labels4rails import gui
from labels4rails import utils
from labels4rails import annotate
from labels4rails.utils import config
from labels4rails.scene import target
from labels4rails.annotate.qt_annotator import QtAnnotator
from labels4rails.scene.target import RailDrawOptions, SwitchDrawOptions
from labels4rails.segmentation.qt.input_data.ui import Ui as SegGui
from labels4rails.autolabel.switches import AutoSwitches
from labels4rails.autolabel.tracks import AutoTracks


class QtGUI(QtWidgets.QMainWindow, Ui_MainWindow):
    '''
    signals
    events_signal: emit to init eventhub in Qscene for key events, init hidden standard mouse cursor in viewport when annotator is loaded
    '''

    events_signal = pyqtSignal(tuple)

    def __init__(self, cfg: config.Labels4RailsConfig):
        super().__init__()

        # flag
        self._PATHS_SET: bool = False

        # path
        self._annotations_path: str = ''
        self._image_path: str = ''
        self._camera_path: str = ''

        # var
        self._cfg: config.Labels4RailsConfig = cfg
        self._dataset: data.IDataSet
        self._gui_events: utils.IEventHub = utils.EventHub()
        self._annotator: QtAnnotator
        self.dock_hwPolicy: int

        # update GUI
        self.setupUi(self)
        self.menubar.setNativeMenuBar(False)
        self.listWidget_images.clear()
        self.update_tag_lists_selection()
        self.setWindowTitle('Labels4Rails')
        self._setup_dock_widget()
        self.hide_Qactions(True)
        self.dockWidget.installEventFilter(self)

        # signals
        # widgets
        self.dockWidget.dockLocationChanged.connect(lambda: self.resize_dockWidget(self.dock_hwPolicy))
        self.dockWidget.topLevelChanged.connect(lambda: self._resize_view())
        self.actionShow_Settings.triggered.connect(lambda: self.restore_dockwidget())
        self.actionLoad_Images_Path.triggered.connect(lambda: self.load_path('img'))
        self.actionLoad_Annotations_Path.triggered.connect(lambda: self.load_path('ann'))
        self.actionLoad_Camera_Path.triggered.connect(lambda: self.load_path('cam'))
        self.actionLoad_Chunk.triggered.connect(lambda: self.load_chunk())
        self.actionSee_Shortcuts.triggered.connect(lambda: self.show_manual_popup())
        self.actionExit.triggered.connect(lambda: self.exit_app())
        self.actionGenerate_Segmentation_Masks.triggered.connect(lambda: self.Generate_Segmentation_Masks())

        # self -> child
        self.events_signal.connect(self.graphicsView.transfer_event_signal)

        # cursor bool to ensure cursor is only visible after loading the first scene
        self._show_cursor = False
        self._lock_show_cursor = False

        # setup StatusBar
        self.statusbar.addWidget(self.label_info_status_active)
        self.statusbar.addPermanentWidget(self.label_info_mousepos_active)

    def __call__(self):
        self.setWindowState(QtCore.Qt.WindowMaximized)

    # RESIZING
    def resizeEvent(self, event: QResizeEvent) -> None:
        if event:
            self.dockWidget.setMaximumSize(self.width() - 10, self.height() - 52)
            if self.dockWidget.isFloating():
                self.graphicsView.resize(self.width() - 20, self.height() - 72)
                self.graphicsView.fitInView()
                return
            if self.dockWidgetArea(self.dockWidget) == 1 or self.dockWidgetArea(self.dockWidget) == 2:
                # position: left/right
                self.graphicsView.resize(self.width() - 20 - self.dockWidget.width(), self.height() - 72)
                self.graphicsView.fitInView()
                return
            if self.dockWidgetArea(self.dockWidget) == 4 or self.dockWidgetArea(self.dockWidget) == 8:
                # pos: top/bottom
                self.graphicsView.resize(self.width() - 20, self.height() - 77 - self.dockWidget.height())
                self.graphicsView.fitInView()
                return
        super().resizeEvent(event)

    def eventFilter(self, object_: QDockWidget, event: QEvent) -> bool:
        if self.graphicsView is not None and self._show_cursor:
            # show cursor once
            self.graphicsView.show_cusor()
            self._lock_show_cursor = True
            self._show_cursor = False
        if object_ == self.dockWidget and event.type() == QEvent.Resize and not self.dockWidget.isFloating():
            if self.dockWidgetArea(self.dockWidget) == 1 or self.dockWidgetArea(self.dockWidget) == 2:
                self.graphicsView.resize(
                    self.width() - 20 - self.dockWidget.width(),
                    self.height() - 72
                )
                self.groupBox_tags.resize(self.dockWidget.width() - self.groupBox_tags.x() - 5, 10)
                self.groupBox_tags.resize(self.dockWidget.width() - self.groupBox_tags.x() - 5,
                                          self.groupBox_tags.childrenRect().height() + 30)
                self.dockWidget.resize(self.dockWidget.width(), self.height() - 65)

                return super().eventFilter(object_, event)

            if self.dockWidgetArea(self.dockWidget) == 4 or self.dockWidgetArea(self.dockWidget) == 8:
                self.graphicsView.resize(
                    self.width() - 20,
                    self.height() - 77 - self.dockWidget.height()
                )
                self.groupBox_tags.setGeometry(self.groupBox_tags.x(), self.groupBox_tags.y(),
                                               self.dockWidget.width() - self.groupBox_tags.x() - 5,
                                               self.groupBox_tags.height())
                self.groupBox_tags.setGeometry(self.groupBox_tags.x(), self.groupBox_tags.y(),
                                               self.dockWidget.width() - self.groupBox_tags.x() - 5,
                                               self.groupBox_tags.childrenRect().height() + 30)
                return super().eventFilter(object_, event)
        elif object_ == self.dockWidget and event.type() == QEvent.Resize and self.dockWidget.isFloating():
            self.groupBox_tags.setGeometry(self.groupBox_tags.x(), self.groupBox_tags.y(),
                                           self.dockWidget.width() - self.groupBox_tags.x() - 5,
                                           self.groupBox_tags.height())
            self.groupBox_tags.setGeometry(self.groupBox_tags.x(), self.groupBox_tags.y(),
                                           self.dockWidget.width() - self.groupBox_tags.x() - 5,
                                           self.groupBox_tags.childrenRect().height() + 30)
            return super().eventFilter(object_, event)
        else:
            return super().eventFilter(object_, event)

    # SIGNALS
    def _init_signals(self) -> None:
        # child -> self
        self.graphicsView.mouse_signal.connect(self.print_mouse_pos)
        self.graphicsView.mouse_signal.connect(self.update_aim_device_pos)
        self.graphicsView.datacounter_signal.connect(self.update_scene)
        self.graphicsView.get_scene().update_scene_signal.connect(self.update_scene)
        self.graphicsView.get_scene().update_scene_signal.connect(self.update_aim_device_pos)

        # widgets
        self.pushButton_add_track.clicked.connect(lambda: self.add_track())
        self.pushButton_del_track.clicked.connect(lambda: self.del_track())
        self.pushButton_add_switch.clicked.connect(lambda: self.add_switch())
        self.pushButton_del_switch.clicked.connect(lambda: self.del_switch())
        self.pushButton_track_auto.clicked.connect(lambda: self.auto_labeling_track())
        self.pushButton_switch_auto.clicked.connect(lambda: self.auto_labeling_switch())
        self.listWidget_images.itemClicked.connect(self.load_image)

        self.listWidget_active_switches.itemClicked.connect(lambda: self.active_switch())
        self.listWidget_active_tracks.itemClicked.connect(lambda: self.active_track())
        self.listWidget_track_layout.itemSelectionChanged.connect(lambda: self.active_tag_track_layout())
        self.listWidget_weather.itemSelectionChanged.connect(lambda: self.active_tag_weather())
        self.listWidget_light.itemSelectionChanged.connect(lambda: self.active_tag_light())
        self.listWidget_tod.itemSelectionChanged.connect(lambda: self.active_tag_tod())
        self.listWidget_environment.itemSelectionChanged.connect(lambda: self.active_tag_env())
        self.listWidget_additional.itemSelectionChanged.connect(lambda: self.active_tag_additional())

        self.tabWidget.currentChanged.connect(lambda: self.switch_tab())
        self.checkBox_track_marks.stateChanged.connect(self.track_drawing_marks)
        self.checkBox_track_fill.stateChanged.connect(self.track_drawing_fill)
        self.checkBox_track_grid.stateChanged.connect(self.track_drawing_grid)
        self.checkBox_track_splines.stateChanged.connect(self.track_drawing_splines)
        self.checkBox_switch_marks.stateChanged.connect(self.switch_drawing_marks)
        self.checkBox_switch_box.stateChanged.connect(self.switch_drawing_box)
        self.checkBox_switch_text.stateChanged.connect(self.switch_drawing_text)

        self.radioTEgo.toggled.connect(self.refocus)
        self.radioTLeft.toggled.connect(self.refocus)
        self.radioTRight.toggled.connect(self.refocus)

    def refocus(self):
        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def _disconnect_signals(self) -> None:
        # child -> self
        self.graphicsView.mouse_signal.disconnect()
        self.graphicsView.datacounter_signal.disconnect()
        self.graphicsView.get_scene().update_scene_signal.disconnect()

        # widgets
        self.pushButton_add_track.clicked.disconnect()
        self.pushButton_del_track.clicked.disconnect()
        self.pushButton_add_switch.clicked.disconnect()
        self.pushButton_del_switch.clicked.disconnect()
        self.pushButton_track_auto.clicked.disconnect()
        self.pushButton_switch_auto.clicked.disconnect()

        self.listWidget_active_switches.itemClicked.disconnect()
        self.listWidget_active_tracks.itemClicked.disconnect()
        self.listWidget_track_layout.itemSelectionChanged.disconnect()
        self.listWidget_weather.itemSelectionChanged.disconnect()
        self.listWidget_light.itemSelectionChanged.disconnect()
        self.listWidget_tod.itemSelectionChanged.disconnect()
        self.listWidget_environment.itemSelectionChanged.disconnect()
        self.listWidget_additional.itemSelectionChanged.disconnect()

        self.tabWidget.currentChanged.disconnect()
        self.checkBox_track_marks.stateChanged.disconnect()
        self.checkBox_track_fill.stateChanged.disconnect()
        self.checkBox_track_grid.stateChanged.disconnect()
        self.checkBox_track_splines.stateChanged.disconnect()
        self.checkBox_switch_marks.stateChanged.disconnect()
        self.checkBox_switch_box.stateChanged.disconnect()
        self.checkBox_switch_text.stateChanged.disconnect()

        self.radioTEgo.toggled.disconnect()
        self.radioTLeft.toggled.disconnect()
        self.radioTRight.toggled.disconnect()

    # DOCKWIDGET
    def _setup_dock_widget(self) -> None:
        self.tags_layout: FlowLayout = FlowLayout(
            parent=None,
            margin=0,
            spacing=5
        )
        self.tags_layout.addWidget(self.widget_track_layout)
        self.tags_layout.addWidget(self.widget_weather)
        self.tags_layout.addWidget(self.widget_light)
        self.tags_layout.addWidget(self.widget_tod)
        self.tags_layout.addWidget(self.widget_environment)
        self.tags_layout.addWidget(self.widget_additional)

        self.groupBox_tags.setLayout(self.tags_layout)

        self.temp_layoutWidget: QWidget = QWidget()
        self.scrollArea: QScrollArea = QScrollArea()
        self.dock_layout: FlowLayout = FlowLayout(
            parent=None,
            margin=0,
            spacing=5
        )

        self.dock_hwPolicy = 300
        self._update_dockLayout()

    def _resize_view(self) -> None:

        offset = 90
        margin = 20

        if self.dockWidget.isFloating():
            # maximize view geometry
            rect = self.geometry()
            self.graphicsView.setGeometry(10, 20, rect.width() - margin, rect.height() - offset)
        else:
            if self.dockWidgetArea(self.dockWidget) == 4 or self.dockWidgetArea(self.dockWidget) == 8:
                # adjust view geometry to control panel at top or bottom
                width = self.geometry().width() - margin
                height = self.geometry().height() - offset - self.dock_hwPolicy
                self.graphicsView.setGeometry(10, 20, width, height)
            else:
                # adjust view geometry to control panel at left or right
                width = self.geometry().width() - margin - self.dock_hwPolicy
                height = self.geometry().height() - offset
                self.graphicsView.setGeometry(10, 20, width, height)
        self.graphicsView.fitInView()

    def _update_dockLayout(self) -> None:
        self.dock_layout.addWidget(self.groupBox_images)
        self.dock_layout.addWidget(self.groupBox_annotations)
        self.dock_layout.addWidget(self.groupBox_tags)

        self.temp_layoutWidget.setLayout(self.dock_layout)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(self.temp_layoutWidget)
        self.dockWidget.setWidget(self.scrollArea)

    def resize_dockWidget(self, size) -> None:
        '''
        docking areas
        1: left
        2: right
        4: top
        8: bottom
        '''
        if self.dockWidgetArea(self.dockWidget) == 1 or self.dockWidgetArea(self.dockWidget) == 2:
            self.resizeDocks({self.dockWidget}, {size}, QtCore.Qt.Horizontal)
        elif self.dockWidgetArea(self.dockWidget) == 4 or self.dockWidgetArea(self.dockWidget) == 8:
            self.resizeDocks({self.dockWidget}, {size}, QtCore.Qt.Vertical)

    def restore_dockwidget(self) -> None:
        self.dockWidget.setVisible(True)

    # WORKSPACE
    def update_scene(self, event: int) -> None:
        self.set_imageList_row(event)
        self.update_annotations()

    def update_annotations(self) -> None:
        self._annotator.update_annotations()
        if not self._lock_show_cursor:
            self._show_cursor = True

    def update_aim_device_pos(self, pos) -> None:
        # must, due to multiple signal type connection
        if isinstance(pos, QPoint):
            self._annotator.get_mouse().qt_mouse_callback(pos.x(), pos.y())
        self._annotator.draw_aim_device()

    # IMAGE LIST
    def set_imageList_row(self, event: int) -> None:
        '''
        to disable mouse selection in list: 
        derive QListWidget and overwrite mouse event
        '''
        datacounter = self._annotator.get_datacounter()

        if self.listWidget_images.currentRow() != datacounter and event:
            self.listWidget_images.setCurrentRow(datacounter)
        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)

    def load_images_to_list(self) -> None:
        files = os.listdir(self._image_path)
        files = natsorted(files, alg = ns.IGNORECASE)
        files = self.UTIL_filter_images(files)
        self.listWidget_images.addItems(files)
        self.listWidget_images.setCurrentRow(0)  # first item selected
        self.label_info_status_active.setText(f'{str(self.listWidget_images.count())} items loaded')

    def del_images_from_list(self) -> None:
        self.listWidget_images.clear()

    def load_image_to_workspace(self) -> None:
        self.clear_workspace(mode="scene")

        path = self.UTIL_rebuild_img_path(self.listWidget_images.currentItem().text())
        self.graphicsView.init_view(path)
        self.graphicsView.setFocus()

    # FILE DIALOG
    def load_chunk(self) -> None:
        self.reset_gui()

        paths = QFileDialog.getExistingDirectory(
            self,
            "Select Chunk Directory",
            "",
            QFileDialog.ShowDirsOnly)
        self._annotations_path = str(paths + '/' + 'annotations')
        self._image_path = str(paths + '/' + 'images')
        self._camera_path = str(paths + '/camera/camera.yaml')

        try:
            self.load_images_to_list()
            self.setup_data_paths()
        except:
            self.label_info_status_active.setText(f'Error: see console output for full traceback')

            print(traceback.print_exc())

    def load_path(self, key: str):
        info_flag: bool = True

        if self._PATHS_SET:
            self.label_info_status_active.setText(f'Filedialog: close App to load new files')
            return

        if key == 'cam':
            path = QFileDialog.getOpenFileName(
                parent=self,
                caption="Select Camera Config File",
                directory=os.getcwd(),
                filter='Data File (*.yaml)')
            self._camera_path = path[0]
            print(self._camera_path)
            if not self._camera_path:
                self._PATHS_SET = False
                info_flag = False
                self.actionLoad_Camera_Path.setText("Load Camera Path")
            else:
                self.actionLoad_Camera_Path.setText("Load Camera Path [Done]")
        elif key == 'img':
            self._image_path = QFileDialog.getExistingDirectory(self, "Select Image Directory")
            self.clear_workspace(mode="all")
            if not self._image_path:
                self._PATHS_SET = False
                info_flag = False
                self.actionLoad_Images_Path.setText("Load Images Path")
            else:
                self.load_images_to_list()
                self.actionLoad_Images_Path.setText("Load Images Path [Done]")
        elif key == 'ann':
            self._annotations_path = QFileDialog.getExistingDirectory(self, "Select Annotation Directory")
            if not self._annotations_path:
                self._PATHS_SET = False
                info_flag = False
                self.actionLoad_Annotations_Path.setText("Load Annotations Path")
            else:
                self.actionLoad_Annotations_Path.setText("Load Annotations Path [Done]")
        self.label_info_status_active.setText(f'Filedialog: path[{key}] is {info_flag}')
        self.setup_data_paths()

    # SETUP  
    def setup_data_paths(self) -> None:
        if self._image_path and self._annotations_path and self._camera_path:
            images: config.Images = config.Images(path=self._image_path, extensions=['jpg', 'jpeg', 'png'])
            paths: config.Paths = config.Paths(camera_extrinsic=self._camera_path, images=images,
                                               annotations=self._annotations_path)
            self._dataset = data.DataSet(paths)

            self.setup_tags()
            self.setup_camera()
            self.setup_annotator()
            self._PATHS_SET = True
            self.label_info_status_active.setText(f'Filedialog: all paths {self._PATHS_SET}')
        else:
            self.label_info_status_active.setText(f'Filedialog: all paths {self._PATHS_SET}')

    def setup_camera(self):
        self._camera = utils.camera.Camera(self._dataset[0].camera_cfg)

    def setup_annotator(self):
        self._annotator = QtAnnotator(self._cfg, self._dataset, self._camera, self._gui_events,
                                      self.graphicsView.get_scene())

        self.update_eventhub()

        self.events_signal.emit((self._annotator.get_eventhub(), True))

        self._annotator.get_eventhub().post(gui.GuiEvents.LOAD_SCENE, "")
        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)

        self._update_checkboxes()
        self.update_annotations()
        self._init_signals()
        self.graphicsView.fitInView()

    # UPDATE GUI
    def reset_gui(self) -> None:
        if self._PATHS_SET:
            self._disconnect_signals()
            self._PATHS_SET = False
            self.events_signal.emit((self._gui_events, False))

        self.tabWidget.setCurrentIndex(0)
        self.listWidget_active_switches.clear()
        self.listWidget_active_tracks.clear()
        self.del_images_from_list()
        self.del_tags()
        self.clear_workspace()
        self._clear_checkboxes()

    def del_tags(self) -> None:
        self.listWidget_track_layout.clear()
        self.listWidget_weather.clear()
        self.listWidget_light.clear()
        self.listWidget_tod.clear()
        self.listWidget_environment.clear()
        self.listWidget_additional.clear()

    def setup_tags(self) -> None:
        maxHeight = 0
        maxWidth = 0
        self.listWidget_track_layout.addItems(self._cfg.targets.tags.track_layout)

        heightSizeHint = self.listWidget_track_layout.sizeHintForRow(0) * self.listWidget_track_layout.count()
        if heightSizeHint > maxHeight:
            maxHeight = heightSizeHint
        if self.listWidget_track_layout.sizeHintForColumn(0) > maxWidth:
            maxWidth = self.listWidget_track_layout.sizeHintForColumn(0)

        self.listWidget_weather.addItems(self._cfg.targets.tags.weather)

        heightSizeHint = self.listWidget_weather.sizeHintForRow(0) * self.listWidget_weather.count()
        if heightSizeHint > maxHeight:
            maxHeight = heightSizeHint
        if self.listWidget_weather.sizeHintForColumn(0) > maxWidth:
            maxWidth = self.listWidget_weather.sizeHintForColumn(0)

        self.listWidget_light.addItems(self._cfg.targets.tags.light)

        heightSizeHint = self.listWidget_light.sizeHintForRow(0) * self.listWidget_light.count()
        if heightSizeHint > maxHeight:
            maxHeight = heightSizeHint
        if self.listWidget_light.sizeHintForColumn(0) > maxWidth:
            maxWidth = self.listWidget_light.sizeHintForColumn(0)

        self.listWidget_tod.addItems(self._cfg.targets.tags.time_of_day)

        heightSizeHint = self.listWidget_tod.sizeHintForRow(0) * self.listWidget_tod.count()
        if heightSizeHint > maxHeight:
            maxHeight = heightSizeHint
        if self.listWidget_tod.sizeHintForColumn(0) > maxWidth:
            maxWidth = self.listWidget_tod.sizeHintForColumn(0)

        self.listWidget_environment.addItems(self._cfg.targets.tags.environment)

        heightSizeHint = self.listWidget_environment.sizeHintForRow(0) * self.listWidget_environment.count()
        if heightSizeHint > maxHeight:
            maxHeight = heightSizeHint
        if self.listWidget_environment.sizeHintForColumn(0) > maxWidth:
            maxWidth = self.listWidget_environment.sizeHintForColumn(0)

        self.listWidget_additional.addItems(self._cfg.targets.tags.additional)

        heightSizeHint = self.listWidget_additional.sizeHintForRow(0) * self.listWidget_additional.count()
        if heightSizeHint > maxHeight:
            maxHeight = heightSizeHint
        if self.listWidget_additional.sizeHintForColumn(0) > maxWidth:
            maxWidth = self.listWidget_additional.sizeHintForColumn(0)

        self.listWidget_track_layout.setMaximumHeight(maxHeight + 5)
        self.listWidget_track_layout.setMaximumWidth(maxWidth + 5)
        self.listWidget_weather.setMaximumHeight(maxHeight + 5)
        self.listWidget_weather.setMaximumWidth(maxWidth + 5)
        self.listWidget_light.setMaximumHeight(maxHeight + 5)
        self.listWidget_light.setMaximumWidth(maxWidth + 5)
        self.listWidget_tod.setMaximumHeight(maxHeight + 5)
        self.listWidget_tod.setMaximumWidth(maxWidth + 5)
        self.listWidget_environment.setMaximumHeight(maxHeight + 5)
        self.listWidget_environment.setMaximumWidth(maxWidth + 5)
        self.listWidget_additional.setMaximumHeight(maxHeight + 5)
        self.listWidget_additional.setMaximumWidth(maxWidth + 5)

    def update_tag_lists_selection(self):
        # enable multiselection for tags 
        self.listWidget_track_layout.setSelectionMode(2)
        self.listWidget_environment.setSelectionMode(2)
        self.listWidget_weather.setSelectionMode(2)
        self.listWidget_tod.setSelectionMode(2)
        self.listWidget_light.setSelectionMode(2)
        self.listWidget_additional.setSelectionMode(2)

    def _clear_checkboxes(self) -> None:
        self.checkBox_track_fill.setChecked(False)
        self.checkBox_track_marks.setChecked(False)
        self.checkBox_track_splines.setChecked(False)
        self.checkBox_track_grid.setChecked(False)
        self.checkBox_switch_marks.setChecked(False)
        self.checkBox_switch_box.setChecked(False)
        self.checkBox_switch_text.setChecked(False)

    def _update_checkboxes(self) -> None:
        draw_options = self._annotator.get_strategy_handler()._draw_options

        if self.tabWidget.currentIndex() == 0:
            if RailDrawOptions.FILL in draw_options:
                self.checkBox_track_fill.setChecked(True)
            if RailDrawOptions.MARKS in draw_options:
                self.checkBox_track_marks.setChecked(True)
            if RailDrawOptions.SPLINES in draw_options:
                self.checkBox_track_splines.setChecked(True)
            if RailDrawOptions.CONTOUR in draw_options:
                self.checkBox_track_grid.setChecked(True)
        elif self.tabWidget.currentIndex() == 1:
            if SwitchDrawOptions.MARKS in draw_options:
                self.checkBox_switch_marks.setChecked(True)
            if SwitchDrawOptions.BOUNDING_BOX in draw_options:
                self.checkBox_switch_box.setChecked(True)
            if SwitchDrawOptions.TEXT_LABEL in draw_options:
                self.checkBox_switch_text.setChecked(True)

    def hide_Qactions(self, state: bool) -> None:
        self.actionLoad_Annotations_Path.setVisible(not state)
        self.actionLoad_Camera_Path.setVisible(not state)
        self.actionLoad_Images_Path.setVisible(not state)

    def update_eventhub(self):
        self._annotator.get_eventhub().subscribe(
            gui.GuiEvents.TRACK_LIST_UPDATE, self.update_track_list
        )
        self._annotator.get_eventhub().subscribe(
            gui.GuiEvents.TRACK_UPDATE_SELECTED, self._update_track
        )
        self._annotator.get_eventhub().subscribe(
            gui.GuiEvents.SWITCH_LIST_UPDATE, self.update_switch_list
        )
        self._annotator.get_eventhub().subscribe(
            gui.GuiEvents.TAG_ALL_LISTS_UPDATE, self.update_tags_all
        )
        self._annotator.get_eventhub().subscribe(
            gui.GuiEvents.SWITCH_UPDATE_SELECTED, self._update_switch
        )
        self._annotator.get_eventhub().subscribe(
            gui.GuiEvents.DISPLAY, self.load_image_to_workspace
        )

    def update_track_list(self, track_list: list[str], id_selected_track):
        self.listWidget_active_tracks.clear()
        [self.listWidget_active_tracks.addItem(str(item)) for item in self._annotator.get_scene().tracks.values()]
        if self.listWidget_active_tracks.count():
            if id_selected_track == -1:
                self.listWidget_active_tracks.setCurrentRow(self.listWidget_active_tracks.count() - 1)
                id = findall('[\d]+', self.listWidget_active_tracks.item(self.listWidget_active_tracks.count() - 1).text())
                self._annotator.get_eventhub().post(gui.GuiEvents.TRACK_SELECT,int(id[0]))
            elif id_selected_track >= 0:
                for row_index in range(self.listWidget_active_tracks.count()):
                    id = int(findall('[\d]+', self.listWidget_active_tracks.item(row_index).text())[0])
                    if id == id_selected_track:
                        self.listWidget_active_tracks.setCurrentRow(row_index)
                        break

    def update_switch_list(self, switch_list: list[str]):
        self.listWidget_active_switches.clear()
        [self.listWidget_active_switches.addItem(str(item)) for item in self._annotator.get_scene().switches.values()]

    def update_tags_all(self, tags: list[str]):
        count = self.listWidget_track_layout.receivers(self.listWidget_track_layout.itemSelectionChanged)
        if count > 0:
            self.listWidget_track_layout.itemSelectionChanged.disconnect()
            self.listWidget_weather.itemSelectionChanged.disconnect()
            self.listWidget_light.itemSelectionChanged.disconnect()
            self.listWidget_tod.itemSelectionChanged.disconnect()
            self.listWidget_environment.itemSelectionChanged.disconnect()
            self.listWidget_additional.itemSelectionChanged.disconnect()

            self.listWidget_track_layout.clearSelection()
            self.listWidget_weather.clearSelection()
            self.listWidget_light.clearSelection()
            self.listWidget_tod.clearSelection()
            self.listWidget_environment.clearSelection()
            self.listWidget_additional.clearSelection()
        
        list_items = self.listWidget_track_layout.findItems("*", QtCore.Qt.MatchWrap | QtCore.Qt.MatchWildcard)
        for item in list_items:
            if item.text() in tags["track_layout"]:
                item.setSelected(True)

        list_items = self.listWidget_weather.findItems("*", QtCore.Qt.MatchWrap | QtCore.Qt.MatchWildcard)
        for item in list_items:
            if item.text() in tags["weather"]:
                item.setSelected(True)

        list_items = self.listWidget_light.findItems("*", QtCore.Qt.MatchWrap | QtCore.Qt.MatchWildcard)
        for item in list_items:
            if item.text() in tags["light"]:
                item.setSelected(True)

        list_items = self.listWidget_tod.findItems("*", QtCore.Qt.MatchWrap | QtCore.Qt.MatchWildcard)
        for item in list_items:
            if item.text() in tags["time_of_day"]:
                item.setSelected(True)

        list_items = self.listWidget_environment.findItems("*", QtCore.Qt.MatchWrap | QtCore.Qt.MatchWildcard)
        for item in list_items:
            if item.text() in tags["environment"]:
                item.setSelected(True)

        list_items = self.listWidget_additional.findItems("*", QtCore.Qt.MatchWrap | QtCore.Qt.MatchWildcard)
        for item in list_items:
            if item.text() in tags["additional"]:
                item.setSelected(True)

        if count > 0:
            self.listWidget_track_layout.itemSelectionChanged.connect(lambda: self.active_tag_track_layout())
            self.listWidget_weather.itemSelectionChanged.connect(lambda: self.active_tag_weather())
            self.listWidget_light.itemSelectionChanged.connect(lambda: self.active_tag_light())
            self.listWidget_tod.itemSelectionChanged.connect(lambda: self.active_tag_tod())
            self.listWidget_environment.itemSelectionChanged.connect(lambda: self.active_tag_env())
            self.listWidget_additional.itemSelectionChanged.connect(lambda: self.active_tag_additional())

            list_items[0].setSelected(not list_items[0].isSelected())
            list_items[0].setSelected(not list_items[0].isSelected())


    def _update_track(self):
        if self._annotator._strategy.name == "TRACK" and self.listWidget_active_tracks.currentItem() is not None:
            id = findall('[\d]+', self.listWidget_active_tracks.currentItem().text())
            if self.listWidget_active_tracks.count():
                if self.radioTEgo.isChecked():
                    self._annotator.get_eventhub().post(gui.GuiEvents.TRACK_CHANGE_POSITION, int(id[0]),
                                                        target.TrackPosition.EGO)
                elif self.radioTLeft.isChecked():
                    self._annotator.get_eventhub().post(gui.GuiEvents.TRACK_CHANGE_POSITION, int(id[0]),
                                                        target.TrackPosition.LEFT)
                elif self.radioTRight.isChecked():
                    self._annotator.get_eventhub().post(gui.GuiEvents.TRACK_CHANGE_POSITION, int(id[0]),
                                                    target.TrackPosition.RIGHT)
    def _update_switch(self):
        if self._annotator._strategy.name == "SWITCH" and self.listWidget_active_switches.currentItem() is not None:

            id = findall('[\d]+', self.listWidget_active_switches.currentItem().text())

            if self.listWidget_active_switches.count():
                if self.radioSFork.isChecked() and self.radioSRight.isChecked():
                    self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_CHANGE_SWITCH, int(id[0]),
                                                        target.SwitchKind.FORK, target.SwitchDirection.RIGHT)
                elif self.radioSFork.isChecked() and self.radioSLeft.isChecked():
                    self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_CHANGE_SWITCH, int(id[0]),
                                                        target.SwitchKind.FORK, target.SwitchDirection.LEFT)
                elif self.radioSFork.isChecked() and self.radioSunknownLR.isChecked():
                    self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_CHANGE_SWITCH, int(id[0]),
                                                        target.SwitchKind.FORK, target.SwitchDirection.UNKNOWN)
                elif self.radioSMerge.isChecked() and self.radioSRight.isChecked():
                    self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_CHANGE_SWITCH, int(id[0]),
                                                        target.SwitchKind.MERGE, target.SwitchDirection.RIGHT)
                elif self.radioSMerge.isChecked() and self.radioSLeft.isChecked():
                    self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_CHANGE_SWITCH, int(id[0]),
                                                        target.SwitchKind.MERGE, target.SwitchDirection.LEFT)
                elif self.radioSMerge.isChecked() and self.radioSunknownLR.isChecked():
                    self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_CHANGE_SWITCH, int(id[0]),
                                                        target.SwitchKind.MERGE, target.SwitchDirection.UNKNOWN)
                elif self.radioSunknownFM.isChecked() and self.radioSLeft.isChecked():
                    self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_CHANGE_SWITCH, int(id[0]),
                                                        target.SwitchKind.UNKNOWN, target.SwitchDirection.RIGHT)
                elif self.radioSunknownFM.isChecked() and self.radioSRight.isChecked():
                    self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_CHANGE_SWITCH, int(id[0]),
                                                        target.SwitchKind.UNKNOWN, target.SwitchDirection.LEFT)
                elif self.radioSunknownFM.isChecked() and self.radioSunknownLR.isChecked():
                    self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_CHANGE_SWITCH, int(id[0]),
                                                        target.SwitchKind.UNKNOWN, target.SwitchDirection.UNKNOWN)

    # GUI FUNCTIONS
    def add_track(self):
        if self.radioTEgo.isChecked():
            self._annotator.get_eventhub().post(gui.GuiEvents.TRACK_CREATE_EGO)
        elif self.radioTLeft.isChecked():
            self._annotator.get_eventhub().post(gui.GuiEvents.TRACK_CREATE_LEFT)
        elif self.radioTRight.isChecked():
            self._annotator.get_eventhub().post(gui.GuiEvents.TRACK_CREATE_RIGHT)

        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def del_track(self):
        self._annotator.get_eventhub().post(gui.GuiEvents.TRACK_DELETE)
        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def active_track(self):
        id = findall('[\d]+', self.listWidget_active_tracks.currentItem().text())
        if self.listWidget_active_tracks.count():
            self._annotator.get_eventhub().post(
                gui.GuiEvents.TRACK_SELECT,
                int(id[0])
            )
            self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
            self.update_annotations()

    def add_switch(self):
        if self.radioSFork.isChecked() and self.radioSRight.isChecked():
            self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_FORK_RIGHT)
        elif self.radioSFork.isChecked() and self.radioSLeft.isChecked():
            self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_FORK_LEFT)
        elif self.radioSFork.isChecked() and self.radioSunknownLR.isChecked():
            self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_FORK_UNKNOWN)
        elif self.radioSMerge.isChecked() and self.radioSRight.isChecked():
            self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_MERGE_RIGHT)
        elif self.radioSMerge.isChecked() and self.radioSLeft.isChecked():
            self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_MERGE_LEFT)
        elif self.radioSMerge.isChecked() and self.radioSunknownLR.isChecked():
            self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_MERGE_UNKNOWN)
        elif self.radioSunknownFM.isChecked() and self.radioSLeft.isChecked():
            self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_UNKNOWN_LEFT)
        elif self.radioSunknownFM.isChecked() and self.radioSRight.isChecked():
            self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_UNKNOWN_RIGHT)
        elif self.radioSunknownFM.isChecked() and self.radioSunknownLR.isChecked():
            self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_UNKNOWN_UNKNOWN)

        # select newly added switch
        if self.listWidget_active_switches.count():
            self.listWidget_active_switches.setCurrentRow(self.listWidget_active_switches.count() - 1)
            id = findall('[\d]+',
                         self.listWidget_active_switches.item(self.listWidget_active_switches.count() - 1).text())
            self._annotator.get_eventhub().post(
                gui.GuiEvents.SWITCH_SELECT,
                int(id[0])
            )

        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def del_switch(self):
        self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_DELETE)
        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def active_switch(self):
        id = findall('[\d]+', self.listWidget_active_switches.currentItem().text())
        if self.listWidget_active_switches.count():
            self._annotator.get_eventhub().post(
                gui.GuiEvents.SWITCH_SELECT,
                int(id[0])
            )
            self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
            self.update_annotations()

    def active_tag_track_layout(self):
        tag_list: list[str] = []

        [tag_list.append(item.text()) for item in self.listWidget_track_layout.selectedItems()]
        self._annotator.get_eventhub().post(
            gui.GuiEvents.TAG_TRACK_LAYOUT,
            tag_list, )

        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def active_tag_weather(self):
        tag_list: list[str] = []

        [tag_list.append(item.text()) for item in self.listWidget_weather.selectedItems()]
        self._annotator.get_eventhub().post(
            gui.GuiEvents.TAG_WEATHER,
            tag_list, )

        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def active_tag_light(self):
        tag_list: list[str] = []

        [tag_list.append(item.text()) for item in self.listWidget_light.selectedItems()]
        self._annotator.get_eventhub().post(
            gui.GuiEvents.TAG_LIGHT,
            tag_list, )

        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def active_tag_tod(self):
        tag_list: list[str] = []

        [tag_list.append(item.text()) for item in self.listWidget_tod.selectedItems()]
        self._annotator.get_eventhub().post(
            gui.GuiEvents.TAG_TIME_OF_DAY,
            tag_list, )

        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def active_tag_env(self):
        tag_list: list[str] = []

        [tag_list.append(item.text()) for item in self.listWidget_environment.selectedItems()]
        self._annotator.get_eventhub().post(
            gui.GuiEvents.TAG_ENVIRONMENT,
            tag_list, )

        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def active_tag_additional(self):
        tag_list: list[str] = []

        [tag_list.append(item.text()) for item in self.listWidget_additional.selectedItems()]
        self._annotator.get_eventhub().post(
            gui.GuiEvents.TAG_ADDITIONAL,
            tag_list, )

        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def switch_tab(self):
        '''
        TabWidget Index
        0: track
        1: switch
        '''
        self.clear_workspace(mode="annotation")

        if self.tabWidget.currentIndex() == 0:
            self._annotator.get_eventhub().post(
                gui.GuiEvents.STRATEGY,
                annotate.qt_annotator.AnnotationStrategies.TRACK)
        elif self.tabWidget.currentIndex() == 1:
            self._annotator.get_eventhub().post(
                gui.GuiEvents.STRATEGY,
                annotate.qt_annotator.AnnotationStrategies.SWITCH)

        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)  # mb rm ?
        self._update_checkboxes()
        self.update_annotations()

    def track_drawing_marks(self, state):
        self._annotator.get_eventhub().post(gui.GuiEvents.TRACK_MARKS, bool(state))
        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def track_drawing_fill(self, state):
        self._annotator.get_eventhub().post(gui.GuiEvents.TRACK_FILL, bool(state))
        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def track_drawing_grid(self, state):
        self._annotator.get_eventhub().post(gui.GuiEvents.TRACK_CONTOUR, bool(state))
        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def track_drawing_splines(self, state):
        self._annotator.get_eventhub().post(gui.GuiEvents.TRACK_SPLINES, bool(state))
        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def switch_drawing_box(self, state):
        self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_SHOW_BOX, bool(state))
        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def switch_drawing_text(self, state):
        self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_SHOW_TEXT, bool(state))
        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def switch_drawing_marks(self, state):
        self._annotator.get_eventhub().post(gui.GuiEvents.SWITCH_SHOW_MARKS, bool(state))
        self._annotator.get_eventhub().post(gui.GuiEvents.DISPLAY)
        self.update_annotations()

    def next_clicked(self):
        # self.gui_events.post(gui.GuiEvents.NEXT)
        pass

    def prev_clicked(self):
        # self.gui_events.post(gui.GuiEvents.PREVIOUS)
        pass

    # MENU ACTIONS
    def exit_app(self) -> None:
        if self._PATHS_SET:
            self.clear_workspace(mode="all")
            self._gui_events.post(gui.GuiEvents.EXIT, True)
        sys.exit()

    def closeEvent(self, event):
        self._gui_events.post(gui.GuiEvents.EXIT, True)
        event.accept()

    # UTILS
    def UTIL_filter_images(self, files: list) -> list:
        files = filter(lambda image: image.lower().endswith(('.jpg', '.jpeg', '.png')), files)
        return files

    def UTIL_rebuild_img_path(self, image) -> str:
        return (str(self._image_path + '/' + image))

    def clear_workspace(self, mode: str = "all") -> None:
        '''
        mode 
        all:        rm all items in qscene, reset gui
        scene:      rm all items in qscene
        image:      rm image
        annotation: rm all items in annotation group
        aimdevice:  rm all items in aim device group
        spline:     rm all items in spline group
        '''

        if mode == "all":
            # call to reset view
            [self.graphicsView.get_scene().removeItem(item) for item in self.graphicsView.items()]
            self.listWidget_images.clearSelection()
            self.listWidget_images.clear()
            self.label_info_status_active.setText('workspace cleared')
            # self.graphicsView.reset_scale()
        elif mode == "scene":
            # rm whole scene
            if len(self.graphicsView.items()):
                [self.graphicsView.get_scene().removeItem(item) for item in self.graphicsView.items()]
        elif mode == "image":
            # rm image
            pass
        elif mode == "annotation":
            # rm all annotations
            if len(self.graphicsView.items()):
                for item in self.graphicsView.get_scene().get_annotation_group().childItems():
                    self.graphicsView.get_scene().get_annotation_group().removeFromGroup(item)
        elif mode == "aimdevice":
            # rm aiming device
            if len(self.graphicsView.items()):
                for item in self.graphicsView.get_scene().get_aim_device_group().childItems():
                    self.graphicsView.get_scene().get_aim_device_group().removeFromGroup(item)
        elif mode == "spline":
            # rm splines
            if len(self.graphicsView.items()):
                for item in self.graphicsView.get_scene().get_annotation_spline_group().childItems():
                    self.graphicsView.get_scene().get_annotation_spline_group().removeFromGroup(item)
        else:
            print('ERR: clear workspace 1')

    # INFO 
    def show_manual_popup(self) -> None:
        box = QMessageBox()
        box.setWindowTitle("RailLabel Key Bindings")
        box.setText('''    
<b>GENERAL:</b><br>
Q: quit app<br>
N: next scene<br>
B: previous scene<br>
MB2: make cursor (in)visible<br><br>

<b>TRACKS:</b><br>
W: Switch between independent and dual stencil mode<br>
E: update position of selected track<br><br>

&nbsp;&nbsp;<b>Labeling with independent mode:</b><br>
&nbsp;&nbsp;A: set mark on left rail<br>
&nbsp;&nbsp;D: set mark on right rail<br>
&nbsp;&nbsp;R: remove mark<br><br>

&nbsp;&nbsp;<b>Labeling with dual stencil mode:</b><br>
&nbsp;&nbsp;F: set marks<br>
&nbsp;&nbsp;R: remove mark under cursor<br>
&nbsp;&nbsp;S: swap stencil side<br>
&nbsp;&nbsp;D: increase distance of stencil<br>
&nbsp;&nbsp;A: decrease distance of stencil<br>
&nbsp;&nbsp;+: increase stencil angle<br>
&nbsp;&nbsp;-: decrease stencil angle<br><br>

<b>TAGS:</b><br>
T: copy tags from prev scene<br>
O: copy tags from prev scene, overwrite existent tag groups<br><br>

<b>SWITCHES:</b><br>
F: set mark<br>
R: remove mark<br>
E: update attributes of selected switch<br>

'''
                    )
        box.exec_()

    def print_mouse_pos(self, pos) -> None:
        self.label_info_mousepos_active.setText(f'x:{pos.x()}, y:{pos.y()}')

    def INFO_get_Qview_items(self) -> None:
        print(str(len(self.graphicsView.get_scene().items())) + ' items in QGscene')
        print(str(len(self.graphicsView.items())) + ' items in QGview')
        [print(item) for item in self.graphicsView.get_scene().items()]

    def auto_labeling_track(self):
        self.autolabel_tracks = AutoTracks(annotator=self._annotator, cfg=self._cfg, dataset=self._dataset, gui_event=self._gui_events)
        self._annotator.get_eventhub().post(gui.GuiEvents.AUTO_LABELING_TRACK)

    def auto_labeling_switch(self):
        self.autolabel_switch = AutoSwitches(annotator=self._annotator, cfg=self._cfg, dataset=self._dataset, gui_event=self._gui_events)
        self._annotator.get_eventhub().post(gui.GuiEvents.AUTO_LABELING_SWITCH)

    def load_image(self, clicked):
        self._annotator.get_eventhub().post(gui.GuiEvents.LOAD_SCENE, clicked.text())
        self.update_scene(1)
        
    def Generate_Segmentation_Masks(self):
        self.hide()
        self.ui_segmentation = SegGui(self)
        self.ui_segmentation.show()