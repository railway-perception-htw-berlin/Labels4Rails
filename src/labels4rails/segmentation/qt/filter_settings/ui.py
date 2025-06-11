import os

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QListView, QTreeView, QAbstractItemView, QMessageBox, QFileDialog, QTreeWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal

from labels4rails.segmentation.qt.filter_settings.ui_init import Ui_MainWindow
from labels4rails.segmentation.qt.output_data.ui import Ui as NextWindow
from labels4rails.segmentation.json_helpers import load_dict_from_json, dump_dict_to_json

def load_annotation_file(json_fname):
    anno_data = load_dict_from_json(json_fname)

    count = { 'tracks' : 0, 'switches' : 0}
    if anno_data['tracks'].keys(): count['tracks'] = len(anno_data['tracks'].keys())
    if anno_data['switches'].keys(): count['switches'] = len(anno_data['switches'].keys())

    tag_list = []
    for k, v in anno_data['tag groups'].items():
        tag_list += v
        if 'unknown' in tag_list: tag_list[tag_list.index('unknown')] = k + '_unknown'

    for k, v in anno_data['switches'].items():
        tag_list += ['switch_' + v['direction']]
        tag_list += [v['kind']]
        
    for k, v in anno_data['tracks'].items():
        tag_list += [v['relative position']]
        
    tag_list = sorted(list(set(tag_list)))
        
    return tag_list, count

class Ui(QtWidgets.QMainWindow):
    def __init__(self, data_dict, previous_window=None, parent=None):
        super(Ui, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.data_dict = data_dict
        
        # Keep a reference to MainWindow
        self.parent = parent
        self.prevous_window = previous_window

        # Init UI elements
        self.load_input_data()
        
        # Connect button in Ui_SegmentationMainWindow to close itself
        self.ui.pushButton_Next.clicked.connect(lambda: self.pushButton_Next())
        self.ui.pushButton_Back.clicked.connect(lambda: self.pushButton_Back())
        # Connect all checkboxes to the state change handler
        for checkbox in self.findChildren(QtWidgets.QCheckBox):
            checkbox.stateChanged.connect(self.load_output_data)
        self.ui.comboBox_include.currentIndexChanged.connect(self.load_output_data)
        self.ui.comboBox_exclude.currentIndexChanged.connect(self.load_output_data)
        self.ui.comboBox_switches.currentIndexChanged.connect(self.load_input_data)
        self.ui.comboBox_tracks.currentIndexChanged.connect(self.load_input_data)
        self.ui.spinBox_switches.valueChanged.connect(self.load_input_data)
        self.ui.spinBox_tracks.valueChanged.connect(self.load_input_data)
    
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
        self.next_ui = NextWindow(self.data_dict, previous_window=self, parent=self.parent)
        self.next_ui.show()
        
    def pushButton_Back(self):      
        # Show prev window
        self.hide()
        self.next_ui = self.prevous_window.show()
        
    def load_input_data(self):
        self.input_image_tags = {}
        self.input_counts = {}
        self.count = {
            'tracks' : self.ui.spinBox_tracks.value(),
            'switches' : self.ui.spinBox_switches.value()
        }
        for folder in self.data_dict['selected_input_folders']:
            annotation_folder = os.path.join(folder, 'annotations')
            annotation_list = sorted([file for file in os.listdir(annotation_folder) if file.endswith(".json")])
            # print(f'length of annotation file list in folder "{folder}" = {len(annotation_list)}')
            for annotation_file in annotation_list:
                image_name = os.path.splitext(annotation_file)[0]
                tag_list, count = load_annotation_file(os.path.join(annotation_folder,annotation_file))
                # print(count, end=' ')
                if self.count_check(count):
                    self.input_image_tags[image_name] = tag_list
                    self.input_counts[image_name] = count
        # print(f'total images loaded during input data : {len(self.input_image_tags)}')
        self.populate_input_stats()
        self.load_output_data()
        
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
        self.get_user_selection_tags()
        self.output_image_list = []
        self.filter_images()
        self.ui.label_DataCount.setText(f"Data Count = ({len(self.output_image_list)})")
        
    def get_user_selection_tags(self):
        A = []; B = []; C = []; D = [];
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
        if self.ui.comboBox_include.currentIndex() == 0: A = included
        else: B = included
        if self.ui.comboBox_exclude.currentIndex() == 0: C = excluded
        else: D = excluded
        self.user_selections = {'A' : A, 'B' : B, 'C' : C, 'D' : D}

    def filter_images(self):
        """
        input data = self.input_image_tags = { 'image name' : [list of tags (str)] }
        returns self.output_image_list = [list of image names based on following rules]
        A-Images are included that contain all of the selected tags (AND) -- All included if no tag is selected
        B-Images are included that contain at least one of the selected tags (OR)
        C-Images are excluded that contain all of the selected tags (AND)
        D-Images are excluded that contain at least one of the selected tags (OR)
        """
        self.include_A()
        self.include_B()
        self.exclude_C()
        self.exclude_D()
    
    def count_check(self, count):
        
        if self.ui.comboBox_tracks.currentIndex()==0: track_check = ( count['tracks'] == self.count['tracks'])
        elif self.ui.comboBox_tracks.currentIndex()==1: track_check = ( count['tracks'] >= self.count['tracks'])
        else : track_check = ( count['tracks'] <= self.count['tracks'])

        if self.ui.comboBox_switches.currentIndex()==0: switch_check = ( count['switches'] == self.count['switches'])
        elif self.ui.comboBox_switches.currentIndex()==1: switch_check = ( count['switches'] >= self.count['switches'])
        else : switch_check = ( count['switches'] <= self.count['switches'])

        # print(f"{count['tracks']} {self.ui.comboBox_tracks.currentText()} {self.count['tracks']} = {track_check}", end=' ')
        # print(f"{count['switches']} {self.ui.comboBox_switches.currentText()} {self.count['switches']} = {switch_check}")
        
        return track_check & switch_check
    
    def include_A(self):
        """
        input data = self.input_image_tags = { 'image name' : [list of tags (str)] }
        selected_tags = self.user_selections['A']
        extends self.output_image_list = [list of image names based on following rules]
        A-Images are included that contain all of the selected tags (AND) -- All included if no tag is selected
        Remove duplicates at the end
        """
        # Get the selected tags for 'A'  
        selected_tags = self.user_selections['A']

        # If no tags are selected, include all images  
        if not selected_tags:  
            self.output_image_list.extend(self.input_image_tags.keys())
            return self.output_image_list  

        # Filter images that contain all selected tags and extend the output list  
        self.output_image_list.extend(  
            image_name  
            for image_name, tags in self.input_image_tags.items()  
            if all(tag in tags for tag in selected_tags)
        ) 

        # Remove duplicates from the output list  
        self.output_image_list = list(set(self.output_image_list))  

    def include_B(self):
        """
        input data = self.input_image_tags = { 'image name' : [list of tags (str)] }
        selected_tags = self.user_selections['B']
        extends self.output_image_list = [list of image names based on following rules]
        B-Images are included that contain at least one of the selected tags (OR)
        Remove duplicates at the end
        """
        # Get the selected tags for 'B'  
        selected_tags = self.user_selections['B']

         # Filter images that contain at least one selected tag and extend the output list  
        self.output_image_list.extend(  
            image_name  
            for image_name, tags in self.input_image_tags.items()  
            if any(tag in tags for tag in selected_tags)
        )  

        # Remove duplicates from the output list  
        self.output_image_list = list(set(self.output_image_list))
    
    def exclude_C(self):
        """
        input data = self.input_image_tags = { 'image name' : [list of tags (str)] }
        self.output_image_list = [list of 'image names' that are already included]
        selected_tags = self.user_selections['C']
        updates self.output_image_list = [list of 'image names' based on following criteria]
        C-Images are excluded that contain all of the selected tags (AND)
        """
        # Get the selected tags for 'C'  
        selected_tags = self.user_selections['C']

        # If no tags are selected, do not exclude any images  
        if not selected_tags:  return self.output_image_list  

        # Filter out images that contain all selected tags  
        self.output_image_list = [  
            image_name  
            for image_name in self.output_image_list  
            if image_name not in self.input_image_tags or  
            not all(tag in self.input_image_tags[image_name] for tag in selected_tags)  
        ]

    def exclude_D(self):
        """
        input data = self.input_image_tags = { 'image name' : [list of tags (str)] }
        self.output_image_list = [list of 'image names' that are already included]
        selected_tags = self.user_selections['D']
        updates self.output_image_list = [list of 'image names' based on following criteria]
        D-Images are excluded that contain at least one of the selected tags (OR)
        """
        # Get the selected tags for 'D'  
        selected_tags = self.user_selections['D']

        # If no tags are selected, do not exclude any images  
        if not selected_tags:  return self.output_image_list  

        # Filter out images that contain at least one of the selected tags 
        self.output_image_list = [  
            image_name  
            for image_name in self.output_image_list  
            if image_name not in self.input_image_tags or  
            not any(tag in self.input_image_tags[image_name] for tag in selected_tags)  
        ]