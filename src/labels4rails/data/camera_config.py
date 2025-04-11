from typing import Union
import abc
import pathlib
import cv2
import numpy as np
import numpy.typing as npt


# replace cv2.FileStorage in _read_camera


class ICameraReader(metaclass=abc.ABCMeta):
    """
    Read camera intrinsics.
    """

    @abc.abstractmethod
    def __init__(self, yaml_path: Union[pathlib.Path, str]) -> None:
        """
        :param yaml_path: Path to camera file
        """
        pass

    @property
    @abc.abstractmethod
    def roll(self):
        pass

    @property
    @abc.abstractmethod
    def pitch(self):
        pass

    @property
    @abc.abstractmethod
    def yaw(self):
        pass

    @property
    @abc.abstractmethod
    def width(self):
        pass

    @property
    @abc.abstractmethod
    def height(self):
        pass

    @property
    @abc.abstractmethod
    def f(self):
        pass

    @property
    @abc.abstractmethod
    def tvec(self):
        pass

    @property
    @abc.abstractmethod
    def camera_matrix(self):
        pass

    @property
    @abc.abstractmethod
    def distortion_coefficients(self):
        pass


class OpenCVCameraReader(ICameraReader):
    """
    Read camera intrinsics from OpenCV style yaml.
    """

    def __init__(self, yaml_path: Union[pathlib.Path, str]) -> None:
        self._path: Union[pathlib.Path, str] = yaml_path
        self._read_camera()
        self._roll = None
        self._pitch = None
        self._yaw = None
        self._width = None
        self._height = None
        self._f = None
        self._tvec = None
        self._camera_matrix = None
        self._distortion_coefficients = None
        self._read_camera()

    def _read_camera(self) -> None:
        """
        Read in data from OpenCV style yaml.
        """
        if not self._path.is_file():
        # if not self._path:
            msg: str = "Could not find camera calibration file."
            raise FileNotFoundError(msg)

        calibration_file = cv2.FileStorage(str(self._path), cv2.FileStorage_READ)
        numbers = calibration_file.getNode("distortion_coefficients")
        dest_coef = []
        for i in range(0, numbers.size()):
            dest_coef.append(numbers.at(i).real())
        dest_coef = np.array(dest_coef)

        self._roll = calibration_file.getNode("roll").real()
        self._pitch = calibration_file.getNode("pitch").real()
        self._yaw = calibration_file.getNode("yaw").real()
        self._width = calibration_file.getNode("width").real()
        self._height = calibration_file.getNode("height").real()
        self._f = calibration_file.getNode("f").real()
        self._tvec = calibration_file.getNode("tvec").mat()
        self._camera_matrix = calibration_file.getNode("camera_matrix").mat()
        self._distortion_coefficients = dest_coef
        calibration_file.release()

    @property
    def roll(self) -> npt.NDArray[np.float_]:
        return self._roll

    @property
    def pitch(self) -> npt.NDArray[np.float_]:
        return self._pitch

    @property
    def yaw(self) -> npt.NDArray[np.float_]:
        return self._yaw

    @property
    def width(self) -> npt.NDArray[np.float_]:
        return self._width

    @property
    def height(self) -> npt.NDArray[np.float_]:
        return self._height

    @property
    def f(self) -> npt.NDArray[np.float_]:
        return self._f

    @property
    def tvec(self) -> npt.NDArray[np.float_]:
        return self._tvec

    @property
    def camera_matrix(self) -> npt.NDArray[np.float_]:
        return self._camera_matrix

    @property
    def distortion_coefficients(self) -> npt.NDArray[np.float_]:
        return self._distortion_coefficients
