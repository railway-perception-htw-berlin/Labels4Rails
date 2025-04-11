import os

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QListView, QTreeView, QAbstractItemView, QMessageBox, QFileDialog, QTreeWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal

from labels4rails.segmentation.gui_init import Ui_SegmentationMainWindow
from labels4rails.segmentation.raillabel2pixelmask import main as generate_segmentation_masks
from labels4rails.segmentation.filter_gui import FilterGui, apply_filter_settings

class GenerateSegmentationThread(QThread):
    progress_updated = pyqtSignal(int)  # Signal to update progress bar

    def __init__(self, input_folders, output_folder):
        super().__init__()
        self.input_folders = input_folders
        self.output_folder = output_folder

    def run(self):
        total = len(self.input_folders)
        for i, input_folder in enumerate(self.input_folders):
            print(input_folder, self.output_folder)
            generate_segmentation_masks([input_folder], self.output_folder, None)
            apply_filter_settings(input_folder, self.output_folder)
            progress = int((i + 1) * 100 / total)
            self.progress_updated.emit(progress)  # Emit progress for each step

class SegGui(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(SegGui, self).__init__(parent)
        self.ui = Ui_SegmentationMainWindow()
        self.ui.setupUi(self)
        
        # Init UI elements
        self.ui.textEdit_InputFolder.hide()
        self.ui.label_OutputFolder.hide()
        self.ui.pushButton_OutputFolder.hide()
        self.ui.textEdit_OutputFolder.hide()
        self.ui.pushButton_Generate.hide()
        self.ui.label_ProgressBar.hide()
        self.ui.progressBar.hide()
        self.ui.label_Proceed.hide()
        self.ui.pushButton_Proceed.hide()
        self.ui.treeWidget.hide()
        self.ui.pushButton_FilterSettings.hide()
        self.ui.label_FilterSettings.hide()
        self.ui.label_InputImageCount.hide()
        self.ui.label_OutputImageCount.hide()
        
        # Connect button in Ui_SegmentationMainWindow to close itself
        self.ui.pushButton_Generate.clicked.connect(lambda: self.pushButton_Generate_clicked())
        self.ui.pushButton_InputFolder.clicked.connect(lambda: self.pushButton_InputFolder_clicked())
        self.ui.pushButton_OutputFolder.clicked.connect(lambda: self.pushButton_OutputFolder_clicked())
        self.ui.pushButton_Proceed.clicked.connect(lambda: self.pushButton_Proceed())
        self.ui.pushButton_FilterSettings.clicked.connect(lambda: self.pushButton_FilterSettings_clicked())
        self.ui.treeWidget.itemSelectionChanged.connect(lambda: self.on_tree_item_selection_changed())
        self.parent = parent  # Keep a reference to MainWindow
    
    def add_folders_to_tree(self, folder_path, parent_item=None):
        # Recursively add folders to tree
        for item in sorted(os.listdir(folder_path)):
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path):  # Only add directories
                tree_item = QTreeWidgetItem([item])
                # If a parent item is provided, add this item as its child
                if parent_item:
                    parent_item.addChild(tree_item)
                else:
                    self.ui.treeWidget.addTopLevelItem(tree_item)
                # Recursively add subdirectories
                self.add_folders_to_tree(item_path, tree_item)
                
    def get_selection_from_tree(self):
        # Get selected folders and print them as a list
        selected_items = self.ui.treeWidget.selectedItems()
        selected_paths = []
        for item in selected_items:
            # Get the full path by traversing up the tree
            folder_path = item.text(0)
            parent = item.parent()
            while parent:
                folder_path = os.path.join(parent.text(0), folder_path)
                parent = parent.parent()
            folder_path = os.path.join(self.input_parent_folder, folder_path) 
            if not os.path.isdir(os.path.join(folder_path,'annotations')):
                QMessageBox.information(self, "Message", f"{folder_path} is not a valid annotated chunk!\nSelect valid annotated chunks!")
                item.setSelected(False)
            else: selected_paths.append(folder_path)
        return selected_paths
    
    def on_tree_item_selection_changed(self):
        self.selected_input_folders = self.get_selection_from_tree()
        self.total_input_images = 0
        for folder in self.selected_input_folders:
            self.total_input_images += len(os.listdir(os.path.join(folder,'images')))
        self.ui.label_InputImageCount.setText(f'Total selected input images = {self.total_input_images}')
        self.ui.label_InputImageCount.show()
        print(self.selected_input_folders, self.total_input_images)
    
    def closeEvent(self, event):
        self.parent.show()  # Show MainWindow again
        self.parent.setWindowState(QtCore.Qt.WindowMaximized)
        event.accept()  # Accept the close event to proceed with closing the window
    
    def pushButton_InputFolder_clicked(self):
        self.input_parent_folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        self.ui.textEdit_InputFolder.setText(self.input_parent_folder)
        self.ui.textEdit_InputFolder.show()
        if not self.input_parent_folder:
            QMessageBox.information(self, "Message", "Select valid folder!")
            return
        self.ui.treeWidget.clear()  # Clear any previous items
        self.add_folders_to_tree(self.input_parent_folder)
        self.ui.treeWidget.show()
        self.ui.label_Proceed.show()
        self.ui.pushButton_Proceed.show()
        
    def pushButton_Proceed(self):
        # self.ui.textEdit_InputFolder.show()
        if not self.selected_input_folders:
            QMessageBox.information(self, "Message", "No folder selected!\nSelect valid annotated chunks!")
            return
        self.ui.label_OutputFolder.show()
        self.ui.pushButton_OutputFolder.show()
    
    def pushButton_OutputFolder_clicked(self):
        self.output_folder = QFileDialog.getExistingDirectory(self, "Select Ouput Folder")
        self.ui.textEdit_OutputFolder.setText(self.output_folder)
        self.ui.textEdit_OutputFolder.show()
        self.ui.pushButton_FilterSettings.show()
        self.ui.label_FilterSettings.show()

    def pushButton_FilterSettings_clicked(self):
        self.hide()
        self.ui_filter = FilterGui(input_folder_list=self.selected_input_folders, parent=self)
        self.ui_filter.show()
        print('fui shown')
        self.ui.pushButton_Generate.show()
        
    def pushButton_Generate_clicked(self):
        # Set initial progress label and show the progress bar
        self.ui.label_ProgressBar.setText('Generating segmentation masks ...')
        self.ui.label_ProgressBar.show()
        self.ui.progressBar.show()
        self.ui.progressBar.setValue(0)

        # Set up and start the worker thread
        self.worker = GenerateSegmentationThread(self.selected_input_folders, self.output_folder)
        self.worker.progress_updated.connect(self.ui.progressBar.setValue)  # Connect signal to progress bar
        self.worker.finished.connect(self.on_generation_finished)  # Optionally handle when the thread finishes
        self.worker.start()

    def on_generation_finished(self):
        # Set progress to 100% and update the label when done
        self.ui.progressBar.setValue(100)
        self.ui.label_ProgressBar.setText('Segmentation masks generated successfully.')
        QMessageBox.information(self, "Message", "Segmentation masks generated successfully\nReturning to main window.")
        self.close()