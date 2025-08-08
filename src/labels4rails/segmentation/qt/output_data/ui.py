import os
import shutil
import ctypes
import platform

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QListView, QTreeView, QAbstractItemView, QMessageBox, QFileDialog, QTreeWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal
from PIL import Image

from labels4rails.segmentation.qt.output_data.ui_init import Ui_MainWindow
from labels4rails.segmentation.raillabel2pixelmask import main as generate_segmentation_masks
from labels4rails.segmentation.raillabel2YOLO import main as generate_yolo_masks

# constants
seg_folder_name = 'segmentation'
yolo_folder_name = 'yolo'
images_folder_name = 'images'
annotations_folder_name = 'annotations'

# check if script is running as adming or not
def is_admin():  
    try:  return ctypes.windll.shell32.IsUserAnAdmin() != 0  
    except: return False


# for segmentation mask generation and applying filter settings
class GenerateSegmentationThread(QThread):
    progress_updated = pyqtSignal(int)  # Signal to update progress bar

    def __init__(self, ui, data_dict):
        super().__init__()
        self.ui = ui
        self.data_dict = data_dict
        self.input_folders = data_dict['selected_input_folders']
        self.output_folder = data_dict['output_folder']
        self.track_segmentation = data_dict['track_segmentation']
        self.generate_segmentation_check = self.data_dict['generate_segmentation_check']
        self.generate_switch_bounding_box_check = self.data_dict['generate_switch_bounding_box_check']
        self.symlink_check = data_dict['symlink_check']
        self.copy_images_check = data_dict['copy_images_check']
        self.copy_annotations_check = data_dict['copy_annotations_check']
        
        # create output folders
        self.segmentation_output_path = os.path.join(self.output_folder, seg_folder_name)
        self.yolo_output_path = os.path.join(self.output_folder, yolo_folder_name)
        self.images_path = os.path.join(self.output_folder, images_folder_name)
        self.annotations_path = os.path.join(self.output_folder, annotations_folder_name)
        
        # create output folder if it does not exist
        os.makedirs(self.output_folder, exist_ok=True)
        # remove contents of the output folder for new data
        shutil.rmtree(self.output_folder)
        # create folders inside the output folder as per user selections
        if self.generate_segmentation_check: os.makedirs(self.segmentation_output_path, exist_ok=True)
        if self.generate_switch_bounding_box_check: os.makedirs(self.yolo_output_path, exist_ok=True)
        if self.copy_images_check: os.makedirs(self.images_path, exist_ok=True)
        if self.copy_annotations_check: os.makedirs(self.annotations_path, exist_ok=True)

    def run(self):
        total = 2*len(self.input_folders)
        progress = 0
        progress_increment = 100/total
        for i, input_folder in enumerate(self.input_folders):
            
            input_folder_name = os.path.split(input_folder)[-1]
            
            if self.generate_segmentation_check:
                self.ui.label_ProgressBar.setText(f'Generating segmentation masks for {input_folder_name}')
                generate_segmentation_masks([input_folder], self.segmentation_output_path, self.track_segmentation, None)
            
            progress += progress_increment
            self.progress_updated.emit(progress)  # Emit progress for each step
            
            if self.generate_switch_bounding_box_check:
                self.ui.label_ProgressBar.setText(f'Generating yolo bounding boxes for {input_folder_name}')
                generate_yolo_masks(input_folder, self.yolo_output_path, None)
            
            progress += progress_increment
            self.progress_updated.emit(progress)  # Emit progress for each step

            if self.copy_images_check: self.copy_images(input_folder=input_folder, symlink=self.symlink_check)
            if self.copy_annotations_check: self.copy_annotations(input_folder=input_folder, symlink=self.symlink_check)
            
        self.ui.label_ProgressBar.setText(f'Applying filter settings ...')
        self.apply_filter_settings()

    def apply_filter_settings(self):
        if self.generate_segmentation_check:
            for fname in sorted(os.listdir(self.segmentation_output_path)):
                fpath = os.path.join(self.segmentation_output_path, fname)
                fname = fname.split('.png')[0]
                if fname not in self.data_dict['output_images_list']: os.remove(fpath)

        if self.generate_switch_bounding_box_check:    
            for fname in sorted(os.listdir(self.yolo_output_path)):
                fpath = os.path.join(self.yolo_output_path, fname)
                fname = fname.split('.txt')[0]
                if fname not in self.data_dict['output_images_list']: os.remove(fpath)

        if self.copy_images_check:
            for fname in sorted(os.listdir(self.images_path)):
                fpath = os.path.join(self.images_path, fname)
                fname = fname.split('.png')[0]
                if fname not in self.data_dict['output_images_list']: os.remove(fpath)

        if self.copy_annotations_check:
            for fname in sorted(os.listdir(self.annotations_path)):
                fpath = os.path.join(self.annotations_path, fname)
                fname = fname.split('.json')[0]
                if fname not in self.data_dict['output_images_list']: os.remove(fpath)

    def copy_images(self, input_folder, symlink=True):
        input_folder = os.path.join(input_folder, 'images')
        for f in sorted(os.listdir(input_folder)):
            if f.lower().endswith(".png"):
                source = os.path.join(input_folder, f)  
                destination = os.path.join(self.images_path, f)  
                if symlink: os.symlink(source, destination)
                else: shutil.copy(source, destination)
    
    def copy_annotations(self, input_folder, symlink=True):
        input_folder = os.path.join(input_folder, 'annotations')
        for f in sorted(os.listdir(input_folder)):
            if f.lower().endswith(".json"):
                source = os.path.join(input_folder, f)  
                destination = os.path.join(self.annotations_path, f)
                if symlink: os.symlink(source, destination)
                else: shutil.copy(source, destination)

class Ui(QtWidgets.QMainWindow):
    def __init__(self, data_dict, previous_window=None, parent=None):
        super(Ui, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.data_dict = data_dict
        self.data_dict['output_folder'] = None
        self.ui.label_DataCount.setText(f"Data Count = {self.data_dict['total_input_images']}")
        
        # Keep a reference to MainWindow
        self.parent = parent
        self.prevous_window = previous_window

        # Init UI elements
        
        # Connect button in Ui_SegmentationMainWindow to close itself
        self.ui.pushButton_CreateData.clicked.connect(lambda: self.pushButton_CreateData())
        self.ui.pushButton_Back.clicked.connect(lambda: self.pushButton_Back())
        self.ui.pushButton_OutputFolder.clicked.connect(lambda: self.pushButton_OutputFolder_clicked())
    
    def closeEvent(self, event):
        self.parent.show()  # Show MainWindow again
        self.parent.setWindowState(QtCore.Qt.WindowMaximized)
        event.accept()  # Accept the close event to proceed with closing the window
        
    def pushButton_Back(self):      
        # Show prev window
        self.hide()
        self.next_ui = self.prevous_window.show()
        
    def pushButton_CreateData(self):
        # Check if output folder is selected
        if not self.data_dict['output_folder']:
            QMessageBox.information(self, "Message", "Please select a valid output folder")
            return
        
        if not os.path.isdir(self.data_dict['output_folder']):
            QMessageBox.information(self, "Message", f"{self.data_dict['output_folder']} is not a valid directory")
            return
        
        # Only check for non-empty folder on macOS  
        if platform.system() == "Darwin":  
            if os.listdir(self.data_dict['output_folder']):  # Folder is not empty  
                QMessageBox.information(self, "Message", f"{self.data_dict['output_folder']} is not empty, delete previous data or create new folder")  
                return
        
        if not (self.ui.checkBox_TrackSegmentation.isChecked() or self.ui.checkBox_SwitchBoundingBoxes.isChecked()):
            QMessageBox.information(self, "Message", f"no output option selected!")
            return
        
        # check admin priviliges for linux and windows
        if self.ui.checkBox_copy_images.isChecked() or self.ui.checkBox_copy_annotations.isChecked():
            if self.ui.checkBox_copy_symlinks.isChecked():
                if platform.system() != "Darwin" and not is_admin():
                    QMessageBox.information(self, "Message", f"To copy symlinks, you need to run this script with admin previliges!\nRun script as administrator or uncheck symlink option to create data\nTo run the script as admin, you can run run_as_admin.py instead of __mian__.py")
                    # self.ui.checkBox_copy_symlinks.setChecked(False)
                    return
        
        # Compile output data
        self.data_dict['generate_segmentation_check'] = self.ui.checkBox_TrackSegmentation.isChecked()
        self.data_dict['generate_switch_bounding_box_check'] = self.ui.checkBox_SwitchBoundingBoxes.isChecked()
        self.data_dict['copy_images_check'] = self.ui.checkBox_copy_images.isChecked()
        self.data_dict['copy_annotations_check'] = self.ui.checkBox_copy_annotations.isChecked()
        self.data_dict['symlink_check'] = self.ui.checkBox_copy_symlinks.isChecked()
        self.data_dict['track_segmentation'] = {
            'ego_track' : {
                'left_rail' : self.ui.spinBox_EgoLeft.value(),
                'right_rail' : self.ui.spinBox_EgoRight.value(),
                'track_bed' : self.ui.spinBox_EgoBed.value()
                },
            'left_neighbor_track' : {
                'left_rail' : self.ui.spinBox_LeftLeft.value(),
                'right_rail' : self.ui.spinBox_LeftRight.value(),
                'track_bed' : self.ui.spinBox_LeftBed.value()
                },
            'right_neighbor_track' : {
                'left_rail' : self.ui.spinBox_RightLeft.value(), 
                'right_rail' : self.ui.spinBox_RightRight.value(), 
                'track_bed' : self.ui.spinBox_RightBed.value()
                },
        }
        
        # Set initial progress label and show the progress bar
        self.ui.label_ProgressBar.show()
        self.ui.progressBar.show()
        self.ui.progressBar.setValue(0)

        # Set up and start the worker thread
        self.worker = GenerateSegmentationThread(self.ui, self.data_dict)
        self.worker.progress_updated.connect(self.ui.progressBar.setValue)  # Connect signal to progress bar
        self.worker.finished.connect(self.on_generation_finished)  # Optionally handle when the thread finishes
        self.worker.start()
        
    def on_generation_finished(self):
        # Set progress to 100% and update the label when done
        self.ui.progressBar.setValue(100)
        self.ui.label_ProgressBar.setText('Data created successfully.')
        QMessageBox.information(self, "Message", "Data created successfully\nReturning to main window.")
        self.close()
    
    def pushButton_OutputFolder_clicked(self):
        self.data_dict['output_folder'] = os.path.normpath(QFileDialog.getExistingDirectory(self, "Select Ouput Folder"))
        self.ui.textEdit_OutputFolder.setText(self.data_dict['output_folder'])
    