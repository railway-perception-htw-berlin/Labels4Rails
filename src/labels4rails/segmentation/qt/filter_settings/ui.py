import os

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QListView, QTreeView, QAbstractItemView, QMessageBox, QFileDialog, QTreeWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal

from labels4rails.segmentation.qt.filter_settings.ui_init import Ui_MainWindow
from labels4rails.segmentation.qt.output_data.ui import Ui as NextWindow
from labels4rails.segmentation.json_helpers import load_dict_from_json, dump_dict_to_json

def load_annotation_file(json_fname):
    anno_data = load_dict_from_json(json_fname)

    result = []
    for k, v in anno_data['tag groups'].items():
        result += v

    for k, v in anno_data['switches'].items():
        result += ['switch_' + v['direction']]
        result += [v['kind']]
        
    for k, v in anno_data['tracks'].items():
        result += [v['relative position']]
        
    result = sorted(list(set(result)))
        
    return result

class Ui(QtWidgets.QMainWindow):
    def __init__(self, data_dict, parent=None):
        super(Ui, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.data_dict = data_dict
        
        # Keep a reference to MainWindow
        self.parent = parent

        # Init UI elements
        self.load_input_data()
        self.load_output_data()
        
        # Connect button in Ui_SegmentationMainWindow to close itself
        self.ui.pushButton_Next.clicked.connect(lambda: self.pushButton_Next())
        # Connect all checkboxes to the state change handler
        for checkbox in self.findChildren(QtWidgets.QCheckBox):
            checkbox.stateChanged.connect(self.load_output_data)
    
    def closeEvent(self, event):
        self.parent.show()  # Show MainWindow again
        self.parent.setWindowState(QtCore.Qt.WindowMaximized)
        event.accept()  # Accept the close event to proceed with closing the window
        
    def pushButton_Next(self):
        # checks for correct data
        
        # Compile data
        self.data_dict['input_image_tags'] = self.input_image_tags
        self.data_dict['input_stats'] = self.input_stats
        self.data_dict['user_selected_tags'] = self.user_selections
        self.data_dict['output_images_list'] = self.output_image_list
        self.data_dict['total_input_images'] = len(self.output_image_list)
        
        # Show next window
        self.hide()
        self.next_ui = NextWindow(self.data_dict, self.parent)
        self.next_ui.show()
        
    def load_input_data(self):
        self.input_image_tags = {}
        for folder in self.data_dict['selected_input_folders']:
            annotation_folder = os.path.join(folder, 'annotations')
            annotation_list = sorted([file for file in os.listdir(annotation_folder) if file.endswith(".json")])
            # print(f'length of annotation file list in folder "{folder}" = {len(annotation_list)}')
            for annotation_file in annotation_list:
                image_name = os.path.splitext(annotation_file)[0]
                tag_list = load_annotation_file(os.path.join(annotation_folder,annotation_file))
                self.input_image_tags[image_name] = tag_list
        # print(f'total images loaded during input data : {len(self.input_image_tags)}')
        self.populate_input_stats()
        
    def populate_input_stats(self):
        self.input_stats = {}
        for image, tag_list in self.input_image_tags.items():
            for tag in tag_list:
                if tag not in self.input_stats.keys(): self.input_stats[tag] = 0
                self.input_stats[tag] += 1
        checkboxes = self.findChildren(QtWidgets.QCheckBox)
        for checkbox in checkboxes:
            txt = checkbox.text().split(' ')[0]
            count = self.input_stats[txt] if txt in self.input_stats.keys() else 0
            checkbox.setText(f'{txt} ({count})')
            
    def load_output_data(self):
        self.output_image_list = []
        
        self.user_selections = self.get_user_selection_tags()
        included_set = set(self.user_selections['included'])
        excluded_set = set(self.user_selections['excluded'])
        
        for image_name, tag_list in self.input_image_tags.items():
            # check if any of the tag is in the included or excluded list? (using set intersection)
            tag_needs_2b_included = bool(set(tag_list) & included_set)
            tag_needs_2b_excluded = bool(set(tag_list) & excluded_set)
            # include image in output list if fulfils criteria
            if tag_needs_2b_included and not tag_needs_2b_excluded:
                self.output_image_list.append(image_name)
            
        self.ui.label_DataCount.setText(f"Data Count = ({len(self.output_image_list)})")
        
    def get_user_selection_tags(self):
        included = []
        excluded = []
        checkboxes = self.findChildren(QtWidgets.QCheckBox)
        for checkbox in checkboxes:
        # print(f"Checkbox Text: {checkbox.text()}, Checked: {checkbox.isChecked()}, __name__: {checkbox.objectName()}")
            if checkbox.isChecked():
                if '_2' in checkbox.objectName():
                    excluded.append(checkbox.text().split(' ')[0])
                else:
                    included.append(checkbox.text().split(' ')[0])                    
        tags = {
            'included' : included,
            'excluded' : excluded
        }
        return tags