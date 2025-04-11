import abc
from labels4rails import utils
import cv2

# replaced by qt

class IMouse(metaclass=abc.ABCMeta):
    """
    Store property of mouse callback.
    """

    @abc.abstractmethod
    def mouse_callback(self, event, x, y, flags, param) -> None:
        pass

    @property
    @abc.abstractmethod
    def left_click_position(self) -> utils.geometry.IImagePoint:
        pass

    @property
    @abc.abstractmethod
    def position(self) -> utils.geometry.IImagePoint:
        pass


class OpenCVMouse(IMouse):
    """
    Store property of mouse callback.
    """

    def __init__(self):
        self._left_click_position: utils.geometry.IImagePoint
        self._left_click_position = utils.geometry.ImagePoint(0, 0)
        self._position: utils.geometry.IImagePoint
        self._position = utils.geometry.ImagePoint(1000, 1000)

    def mouse_callback(self, event, x, y, flags, param) -> None:
        """
        Receive call back from OpenCV gui.
        :param event: Event causing the callback
        :param x: X-coordinate of mouse
        :param y: Y-coordinate of mouse
        :param flags:
        :param param:
        """
        if event == cv2.EVENT_LBUTTONDOWN:
            self._left_click_position = utils.geometry.ImagePoint(x, y)
        elif event == cv2.EVENT_MOUSEMOVE:
            self._position = utils.geometry.ImagePoint(x, y)
    
    def qt_mouse_callback(self, x, y):
        self._left_click_position = utils.geometry.ImagePoint(x, y) 
        self._position = utils.geometry.ImagePoint(x, y)

    @property
    def left_click_position(self) -> utils.geometry.IImagePoint:
        return self._left_click_position

    @property
    def position(self) -> utils.geometry.IImagePoint:
        return self._position
