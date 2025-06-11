import os

from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QListView, QTreeView, QAbstractItemView, QMessageBox, QFileDialog, QTreeWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal

from labels4rails.segmentation.qt.input_data.ui_init import Ui_MainWindow
from labels4rails.segmentation.qt.filter_settings.ui import Ui as NextWindow

class Ui(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(Ui, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.treeWidget = CustomTreeWidget(self.ui.centralwidget)
        self.ui.treeWidget.setGeometry(QtCore.QRect(10, 110, 621, 281))
        self.ui.treeWidget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.data_dict = {}
        self.selected_input_folders = None
        self.total_input_images = None
        
        # Keep a reference to MainWindow
        self.parent = parent

        # Init UI elements
        self.ui.pushButton_Next.clicked.connect(lambda: self.pushButton_Next())
        self.ui.pushButton_InputFolder.clicked.connect(lambda: self.pushButton_InputFolder_clicked())
        self.ui.treeWidget.itemSelectionChanged.connect(lambda: self.on_tree_item_selection_changed())
        
        # Connect button in Ui_SegmentationMainWindow to close itself
    
    def closeEvent(self, event):
        self.parent.show()  # Show MainWindow again
        self.parent.setWindowState(QtCore.Qt.WindowMaximized)
        event.accept()  # Accept the close event to proceed with closing the window
        
    def pushButton_Next(self):
        # checks for correct data
        if not self.selected_input_folders:
            QMessageBox.information(self, "Message", "No folder selected!\nSelect valid annotated chunks!")
            return
        
        # Compile data
        self.data_dict['selected_input_folders'] = self.selected_input_folders
        self.data_dict['total_input_images'] = self.total_input_images
        
        # Show next window
        self.hide()
        self.next_ui = NextWindow(self.data_dict, previous_window=self, parent=self.parent)
        self.next_ui.show()
        
    def pushButton_InputFolder_clicked(self):
        self.input_parent_folder = os.path.normpath(QFileDialog.getExistingDirectory(self, "Select Input Folder"))
        self.ui.textEdit.setText(self.input_parent_folder)
        self.ui.textEdit.show()
        if not self.input_parent_folder:
            QMessageBox.information(self, "Message", "Select valid folder!")
            return
        self.ui.treeWidget.clear()  # Clear any previous items
        self.add_folders_to_tree(self.input_parent_folder)
    
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
                
    def on_tree_item_selection_changed(self):
        self.selected_input_folders = self.get_selection_from_tree()
        self.total_input_images = 0
        for folder in self.selected_input_folders:
            self.total_input_images += len(os.listdir(os.path.join(folder,'images')))
        self.ui.label_DataCount.setText(f'Data Count = {self.total_input_images}')
        # print(self.selected_input_folders, self.total_input_images)
    
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
    
class CustomTreeWidget(QtWidgets.QTreeWidget):
    def __init__(self, parent=None):
        super(CustomTreeWidget, self).__init__(parent)
        self.last_selected_item = None  # Keep track of the last selected item for range selection

    def keyPressEvent(self, event):
        # Default behavior for other keys
        super().keyPressEvent(event)
        # once the default behaviour is done (next item is selected), make selections
        current_item = self.currentItem()
        if current_item:
            if event.modifiers() == Qt.ShiftModifier:
                if event.key() in [Qt.Key_Up, Qt.Key_Down]:
                        current_item.setSelected(not current_item.isSelected())
            self.last_selected_item = current_item

    def mousePressEvent(self, event):
        # Call the default mousePressEvent first to do what it can do
        super(CustomTreeWidget, self).mousePressEvent(event)
        # Get the item clicked by the user
        clicked_item = self.itemAt(event.pos())
        # if escape return if no item is selected
        if clicked_item:
            if event.modifiers() == Qt.ShiftModifier and self.last_selected_item:
                # Perform range selection
                self.selectRange(self.last_selected_item, clicked_item)
                clicked_item.setSelected(clicked_item.isSelected())
            self.last_selected_item = clicked_item

    def selectRange(self, start_item, end_item):
        if not start_item or not end_item: return
        visible_items = visible_tree_items(self)
        start_index, end_index = sorted([visible_items.index(start_item), visible_items.index(end_item)])
        if not start_index == end_index:
            for item in visible_items[start_index + 1 : end_index]:
                item.setSelected(not item.isSelected())


def visible_tree_items(tree_widget):
    visible_items = []
    # Process top-level items
    for i in range(tree_widget.topLevelItemCount()):
        top_item = tree_widget.topLevelItem(i)
        visible_items.append(top_item)
        # Only process children of expanded items
        if top_item.isExpanded(): process_visible_children(top_item, visible_items)
    return visible_items

def process_visible_children(parent_item, items_list):
    for i in range(parent_item.childCount()):
        child = parent_item.child(i)
        items_list.append(child)
        # Recursively process children only if this item is expanded
        if child.isExpanded(): process_visible_children(child, items_list)