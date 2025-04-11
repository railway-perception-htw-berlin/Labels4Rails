#!/usr/bin/env python3
import sys
# [ubuntu] use:
# PYTHONPATH=./..  python __main__.py

import os
from labels4rails.utils.config import Labels4RailsConfig
import hydra.core.config_store
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from labels4rails.gui.qt.gui import QtGUI
import traceback

config_store = hydra.core.config_store.ConfigStore.instance()
config_store.store(name="rail_label_config", node=Labels4RailsConfig)
# Color to output the error message as red
CRED = '\033[91m'
CEND = '\033[0m'




def excepthook(exc_type, exc_value, exc_tb):
    """
    From https://stackoverflow.com/questions/55819330/catching-exceptions-raised-in-qapplication (last visited on the
    30.08.2022)
    This method catches the errors and prints them to the console. This is necessary because PYQT is
    threadsafe and the exceptions within the QT thread are not passed to the main thread.

    """
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(20*"---")
    print(CRED+"error message:\n", tb+CEND)
    QApplication.quit()
    # or QtWidgets.QApplication.exit(0)
@hydra.main(config_path="conf", config_name="config")
def main(cfg: Labels4RailsConfig):
    sys.excepthook = excepthook
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    window = QtGUI(cfg)
    window.show()
    window()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
