from typing import Any, Union
import sys

from PyQt5 import QtCore
from PyQt5.QtWidgets import (QGraphicsView, 
    QGraphicsScene, 
    QGraphicsPixmapItem, 
    QGraphicsItemGroup)
from PyQt5.QtGui import ( 
    QPixmap, 
    QMouseEvent, 
    QCursor, 
    QKeyEvent,
)
from PyQt5.QtCore import (
    Qt, 
    pyqtSignal, 
    QPoint,
    QSize)

from labels4rails import utils
from labels4rails import gui
from labels4rails.gui.aiming_devices.track_stencil.track_stencil import QtCircleAimdevice
from labels4rails.gui.aiming_devices.cross_hair.cross_hair import QtCrossAimdeviceLine

class ImageScene(QGraphicsScene):
    '''
    signals
    - scene_datacounter_signal: emit to init a scene change
    - update_scene_signal: emit to init a complete scene update

    groups
    - image_group: contain dataset images (QPixmap/QGraphicsPixmapItems) | not used
    - annotation_group: contains annotations (except splines)
    - aim_device_group: contains aiming device(s)
    - annotation_spline_group: contains all spline annotations
    '''

    # signals
    scene_datacounter_signal = pyqtSignal(int)
    update_scene_signal = pyqtSignal(int)

    def __init__(self):
        super(ImageScene, self).__init__()
        
        self._EVENT: bool = False
        self._last_point: QPoint = QPoint(0, 0)
        self._image_size: QSize = QSize(0, 0)
        self._event: utils.IEventHub
        
        # groups
        self._annotation_group: QGraphicsItemGroup = QGraphicsItemGroup() 
        self._aim_device_group: QGraphicsItemGroup = QGraphicsItemGroup() 
        self._annotation_spline_group: QGraphicsItemGroup = QGraphicsItemGroup()

        # aim device 
        # _aim_device_a is initially AT mouse position
        # _aim_device_b is initially RIGHT NEXT to mouse position
        self._aim_device_a: Union[QtCrossAimdeviceLine, QtCircleAimdevice]
        self._aim_device_b: Union[QtCrossAimdeviceLine, QtCircleAimdevice]

    def get_annotation_group(self) -> QGraphicsItemGroup:
        return self._annotation_group

    def get_annotation_spline_group(self) -> QGraphicsItemGroup:
        return self._annotation_spline_group

    def get_aim_device_group(self) -> QGraphicsItemGroup:
        return self._aim_device_group

    def del_aim_device(self):
        if self._aim_device_group.childItems():
            [self._aim_device_group.removeFromGroup(item) for item in self._aim_device_group.childItems()]

    def set_aim_device_a(self, device) -> None:
        self._aim_device_a = device

    def set_aim_device_b(self, device) -> None:
        self._aim_device_b = device

    def set_image_size(self, image_size) -> None:
        self._image_size = image_size

    # def get_aim_device_a(self, device) -> Union[QtCrossAimdeviceLine, QtCircleAimdevice]:
    def get_aim_device_a(self):
        return self._aim_device_a

    def get_aim_device_b(self):
        return self._aim_device_b

    def get_image_size(self) -> QSize:
        return self._image_size

    def has_aim_device_group(self) -> bool:
        return True if self._aim_device_group in self.items() else False

    def add_aim_device_group(self) -> None:
        self.addItem(self._aim_device_group)        

    def has_annotation_group(self) -> bool:
        return True if self._annotation_group in self.items() else False

    def add_annotation_group(self) -> None:
        self.addItem(self._annotation_group)

    def has_spline_group(self) -> bool:
        return True if self._annotation_spline_group in self.items() else False

    def add_spline_group(self) -> None:
        self.addItem(self._annotation_spline_group)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        '''
        keys
        Q:      quit app
        F:      set mark
        R:      remove mark
        S:      swap stencil side
        D:      inc offset stencil x pos
        A:      decr offset stencil x pos
        Minus:  inc offset stencil's angle
        Plus:   decr offset stencils angle
        N:      next scene
        B:      prev scene
        T:      copy tags from prev scene
        W:      activate independent stencil mode
        E:      update selected switch's attributes

        test keys
        I:      count annotation items
        F1:     list current subscribers
        '''

        if self._EVENT:
            if event.key() == Qt.Key_Q:
                self._event.post(gui.GuiEvents.EXIT, True)
                sys.exit()
            elif event.key() == Qt.Key_F:
                if len(self._aim_device_group.childItems()) == 2:
                    self.update_scene_signal.emit(1)
                self._event.post(gui.GuiEvents.MARK)
                self.update_scene_signal.emit(1)
            elif event.key() == Qt.Key_R: 
                if len(self._aim_device_group.childItems()) == 2:
                    self.update_scene_signal.emit(1)
                self._event.post(gui.GuiEvents.REMOVE)
                self.update_scene_signal.emit(1)
            elif event.key() == Qt.Key_S:
                self._event.post(gui.GuiEvents.TRACK_STENCIL_SIDE)
                self.update_scene_signal.emit(1)
            elif event.key() == Qt.Key_D:
                self._event.post(gui.GuiEvents.TRACK_WIDTH_INCR, 1) 
                self.update_scene_signal.emit(1)
            elif event.key() == Qt.Key_A:
                self._event.post(gui.GuiEvents.TRACK_WIDTH_DECR, -1) 
                self.update_scene_signal.emit(1)
            elif event.key() == Qt.Key_Minus:
                self._event.post(gui.GuiEvents.TRACK_ANGLE_DECR, 1)
                self.update_scene_signal.emit(1)
            elif event.key() == Qt.Key_Plus:
                self._event.post(gui.GuiEvents.TRACK_ANGLE_INCR, -1)
                self.update_scene_signal.emit(1)
            elif event.key() == Qt.Key_N:
                self._event.post(gui.GuiEvents.NEXT)
                self.scene_datacounter_signal.emit(1)
            elif event.key() == Qt.Key_B:
                self._event.post(gui.GuiEvents.PREVIOUS)
                self.scene_datacounter_signal.emit(1)
            elif event.key() == Qt.Key_T:
                self._event.post(gui.GuiEvents.TAG_COPY)
                self.update_scene_signal.emit(1)
            elif event.key() == Qt.Key_O:
                self._event.post(gui.GuiEvents.TAG_COPY_OVERWRITE)
                self.update_scene_signal.emit(1)
            elif event.key() == Qt.Key_W:
                self._event.post(gui.GuiEvents.INDEPENDENT_MODE)
                self.update_scene_signal.emit(1)
            elif event.key() == Qt.Key_E:
                self._event.post(gui.GuiEvents.SWITCH_UPDATE_SELECTED)
                self._event.post(gui.GuiEvents.TRACK_UPDATE_SELECTED)
                self.update_scene_signal.emit(1)
            
            # TEST
            # get num of items in scene
            elif event.key() == Qt.Key_I:
                print('items in scene:')
                for item in self.items():
                    if item == self._annotation_group:
                        print(f'annotations: {len(item.childItems())}')
                    elif item == self._aim_device_group:
                        print(f'aim devices: {len(item.childItems())}')
                    elif item == self._annotation_spline_group:
                        print(f'splines: {len(item.childItems())}')
            # print subscribed events
            elif event.key() == Qt.Key_F1:
                [print(item) for item in self._event.subscribers]

    def get_event_signal(self, event: tuple[utils.IEventHub, bool]) -> None:
        self._event = event[0]
        self._EVENT = True if event[1] else False



class ImageViewer(QGraphicsView):
    '''
    implementation
    scaling: rescales the view when zooming, not the images
    hierarchy: QView <- QScene <- QGPI <- QPixmap

    signals
    mouse_signal:       emit mouse position, mapped to current scene
    mouse_y_signal:     emit y mouse pos, mapped to current scene
    events_signal:      emit to init eventhub in Qscene for key events
    datacounter_signal: emit to init a scene change
    '''
    # signals
    # mouse_y_signal = pyqtSignal(int)
    mouse_signal = pyqtSignal(QPoint)
    events_signal = pyqtSignal(tuple)
    datacounter_signal = pyqtSignal(int)
    
    def __init__(self, parent):
        super(ImageViewer, self).__init__(parent)
        
        self._SHOW_CURSOR: bool = True
        self._cursor_in_view = False
        
        # var
        self.image_scene: ImageScene = ImageScene() 
        self.image: QGraphicsPixmapItem = QGraphicsPixmapItem()
        self._lastPoint: QPoint = QPoint(0,0)
        self.zoom: int = 0
        self.zoom_cap: int = 25 # prevent over-zooming
        self.default_cursor = QCursor(QtCore.Qt.ArrowCursor)

        # init
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setMouseTracking(True)
        self.setScene(self.image_scene)
        self.setTransformationAnchor(QGraphicsView.NoAnchor) # zoom anchor - affect scaling view

        # signals
        # self -> child
        self.events_signal.connect(self.image_scene.get_event_signal)
        # child -> parent
        self.image_scene.scene_datacounter_signal.connect(self.emit_datacounter_signal)

    def fitInView(self, scale=True) -> bool:
        '''
        this is taken from:
        https://stackoverflow.com/questions/35508711/how-to-enable-pan-and-zoom-in-a-qgraphicsview
        '''
        rect = QtCore.QRectF(self.image.pixmap().rect())
        if not rect.isNull():
            
            viewrect = self.rect()
            scenerect = self.transform().mapRect(rect)
            if self.zoom <= 0 or (viewrect.width() > scenerect.width() and viewrect.height() > scenerect.height()):
                self.setSceneRect(rect)
                if self.image and not self.image.pixmap().isNull() and self.image_scene:
                    unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
                    self.scale(1 / unity.width(), 1 / unity.height())
                    viewrect = self.rect()
                    scenerect = self.transform().mapRect(rect)
                    factor = min((viewrect.width()-2) / scenerect.width(),
                                 (viewrect.height()-2) / scenerect.height())
                    self.scale(factor, factor)
                self.zoom = 0
                return True
        return False

    def wheelEvent(self, event: QMouseEvent) -> None:
        if self.image and not self.image.pixmap().isNull() and self.image_scene and self.image_scene.items():
            if event.angleDelta().y() > 0:
                factor = 1.25
                self.zoom += 1
            else:
                factor = 0.8
                self.zoom -= 1

            if self.zoom > 0 and self.zoom <= self.zoom_cap:
                self.scale(factor, factor)
                if self.fitInView():
                    self._lastPoint = self.mapToScene(event.pos()).toPoint()

            elif self.zoom > self.zoom_cap:
                self.zoom = self.zoom_cap
            elif self.fitInView():
                self._lastPoint = self.mapToScene(event.pos()).toPoint()
                
        delta = self.mapToScene(event.pos()).toPoint() - self._lastPoint
        self.translate(delta.x(), delta.y())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.setDragMode(self.ScrollHandDrag)
            super(ImageViewer, self).mousePressEvent(event)
        elif event.button() == Qt.RightButton:
            if self.image_scene._EVENT:
                self.image_scene._event.post(gui.GuiEvents.DRAG,self.mapToScene(event.pos()).toPoint())
                self.image_scene.update_scene_signal.emit(1)
        elif event.button() == Qt.MidButton:
            if not self._SHOW_CURSOR:
                self._SHOW_CURSOR = True
            else:
                self._SHOW_CURSOR = False

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setDragMode(self.NoDrag)
            super(ImageViewer, self).mouseReleaseEvent(event)
        elif event.button() == Qt.RightButton:
            self.image_scene._event.post(gui.GuiEvents.DROP,self.mapToScene(event.pos()).toPoint())
            self.image_scene.update_scene_signal.emit(1)
        if not self._SHOW_CURSOR:
            self.viewport().setCursor(QCursor(QtCore.Qt.BlankCursor))
        else:
            self.viewport().setCursor(self.default_cursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._cursor_in_view = True
        self.mouse_signal.emit(self.mapToScene(event.pos()).toPoint())
        self._lastPoint = self.mapToScene(event.pos()).toPoint()
        super(ImageViewer, self).mouseMoveEvent(event)
    
    def enterEvent(self, event: QMouseEvent) -> None:
        self._cursor_in_view = True
        if not self._SHOW_CURSOR:
            self.viewport().setCursor(QCursor(QtCore.Qt.BlankCursor))
        else:
            self.viewport().setCursor(self.default_cursor)
        super(ImageViewer, self).enterEvent(event)
        self.setFocus()
    
    def leaveEvent(self, event: QMouseEvent) -> None:
        self._cursor_in_view = False
        self.viewport().setCursor(self.default_cursor)
        super(ImageViewer, self).leaveEvent(event)

    def get_image(self) -> QPixmap:
        return self.image
    
    def set_image_to_QPGI(self, image: QPixmap) -> None:
        self.image.setPixmap(image)
        self.image_scene.set_image_size(image.size())

    def get_scene(self) -> QGraphicsScene:
        return self.image_scene
    
    def init_view(self, path: str) -> None:
        self.set_image_to_QPGI(QPixmap(path))
        if self.image not in self.image_scene.items(): 
            self.image_scene.addItem(self.image)
        if not self.image_scene.has_annotation_group(): 
            self.image_scene.add_annotation_group()
        if not self.image_scene.has_aim_device_group():
            self.image_scene.add_aim_device_group()
        if not self.image_scene.has_spline_group():
            self.image_scene.add_spline_group()
        self.show()

    def transfer_event_signal(self, event: tuple[utils.IEventHub, bool]) -> None:
        self.events_signal.emit(event)
        self._SHOW_CURSOR = False if event[1] else True

    def emit_datacounter_signal(self, event: int) -> None:
        self.datacounter_signal.emit(event)

    def show_cusor(self):
        self._SHOW_CURSOR = True
        self.viewport().setCursor(QCursor(QtCore.Qt.ArrowCursor))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if (event.key() != Qt.Key_A and event.key() != Qt.Key_D and event.key() != Qt.Key_F and event.key() != Qt.Key_R):
                self.image_scene.keyPressEvent(event)
        elif self._cursor_in_view:
            self.image_scene.keyPressEvent(event)
