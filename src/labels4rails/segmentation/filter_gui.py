import os, sys

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QListView, QTreeView, QAbstractItemView, QMessageBox, QFileDialog, QTreeWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal

from labels4rails.segmentation.filter_gui_init import Ui_MainWindow
from labels4rails.segmentation.json_helpers import load_dict_from_json, dump_dict_to_json
# from filter_gui_init import Ui_MainWindow
# from json_helpers import load_dict_from_json, dump_dict_to_json

json_name = 'user_tags_for_filtering.json'

def apply_filter_settings(input_folder, output_folder):
    json_file_data = load_dict_from_json(json_name)
    image_tags = json_file_data['input_image_tags']
    user_tags = json_file_data['user_tags']
    input_stats = json_file_data['input_stats']
    # print(input_stats)
    for fname in sorted(os.listdir(output_folder)):
        seg_path = os.path.join(output_folder, fname)
        image_name = fname.split('.png')[0]
        # get image tags
        if image_name not in image_tags.keys(): break
        current_image_tags = image_tags[image_name]
        delete = True # delete flag for deleting undesireable masks at the end of the loop
        # do not delete if not included by user
        for tag in user_tags['included']:
            if tag in current_image_tags:
                # print(f'found {tag} in {current_image_tags}')
                delete = False
                break
        # delete if excluded by user
        for tag in user_tags['excluded']:
            if tag in current_image_tags:
                # print(f'found {tag} in {current_image_tags}')
                delete = True
                break
        if delete:
            # print(f'removing {seg_path}')
            os.remove(seg_path)

def load_annotation_file(json_fname):
    result = []
    tags = load_dict_from_json(json_fname)['tag groups']
    for k in tags.keys():
        result += tags[k]
    result = sorted(list(set(result)) )# remove duplicates
    return result

class FilterGui(QtWidgets.QMainWindow):
    def __init__(self, input_folder_list, parent=None):
        super(FilterGui, self).__init__(parent)
        self.input_folder_list = input_folder_list
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.load_input_data()
        self.load_output_data()
        
        # Connect button in Ui_SegmentationMainWindow to close itself
        self.ui.pushButton_Continue.clicked.connect(lambda: self.pushButton_Continue_clicked())
        
        # Connect all checkboxes to the state change handler
        for checkbox in self.findChildren(QtWidgets.QCheckBox):
            checkbox.stateChanged.connect(self.on_checkbox_state_changed)
        self.parent = parent  # Keep a reference to MainWindow
    
    def closeEvent(self, event):
        if self.parent:
            self.parent.show()  # Show MainWindow again
            self.parent.setWindowState(QtCore.Qt.WindowMaximized)
        event.accept()  # Accept the close event to proceed with closing the window
        
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
    
    def load_input_data(self):
        self.input_image_tags = {}
        for folder in self.input_folder_list:
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
        
        user_selections = self.get_user_selection_tags()
        included_set = set(user_selections['included'])
        excluded_set = set(user_selections['excluded'])
        
        for image_name, tag_list in self.input_image_tags.items():
            # check if any of the tag is in the included or excluded list? (using set intersection)
            tag_needs_2b_included = bool(set(tag_list) & included_set)
            tag_needs_2b_excluded = bool(set(tag_list) & excluded_set)
            # include image in output list if fulfils criteria
            if tag_needs_2b_included and not tag_needs_2b_excluded:
                self.output_image_list.append(image_name)
            
        self.populate_output_stats()
        
    def populate_output_stats(self):
        self.ui.label_ImageCount.setText(f"({len(self.output_image_list)})")
        
    def pushButton_Continue_clicked(self):
        # Your code here
        self.user_tags = self.get_user_selection_tags()
        json_file_data = {
            'input_image_tags' : self.input_image_tags,
            'user_tags' : self.user_tags,
            'input_stats'     : self.input_stats,
            'output_images_list'    : self.output_image_list
        }
        dump_dict_to_json(json_file_data, json_name)
        # Closing the ui
        self.close()
            
    def on_checkbox_state_changed(self):
        self.load_output_data()
        
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Sample input folder list
    parent_folder = "/home/anwer/ws/sm/ccc/Sample/"
    input_folder_list = [parent_folder + i for i in [
        "nordlandsbahn_winter_001",
        "nordlandsbahn_winter_002",
        "nordlandsbahn_winter_003"
        ]]
    output_folder = os.path.join(parent_folder, "delme")

    # Initialize and show the FilterGui
    filter_gui = FilterGui(input_folder_list=input_folder_list)
    filter_gui.show()
    
    apply_filter_settings(input_folder_list[0], output_folder)

    sys.exit(app.exec_())