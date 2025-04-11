import os

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
        self.next_ui = NextWindow(self.data_dict, self.parent)
        self.next_ui.show()
        
    def pushButton_InputFolder_clicked(self):
        self.input_parent_folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
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
    
from PyQt5.QtCore import Qt

class CustomTreeWidget(QtWidgets.QTreeWidget):
    def __init__(self, parent=None):
        super(CustomTreeWidget, self).__init__(parent)
        self.last_selected_item = None  # Keep track of the last selected item for range selection

    def keyPressEvent(self, event):
        if event.key() in [Qt.Key_Up, Qt.Key_Down] and event.modifiers() == Qt.ShiftModifier:
            current_item = self.currentItem()

            if not current_item:
                return super().keyPressEvent(event)

            # Determine the next item
            if event.key() == Qt.Key_Up:
                next_item = self.itemAbove(current_item)
            elif event.key() == Qt.Key_Down:
                next_item = self.itemBelow(current_item)
            else:
                next_item = None

            # Perform range selection if Shift is pressed
            if next_item:
                if not self.last_selected_item:
                    self.last_selected_item = current_item
                self.setCurrentItem(next_item)
                next_item.setSelected(next_item.isSelected())  # Explicitly select the next item
        else:
            # Default behavior for other keys
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        # Get the item clicked by the user
        clicked_item = self.itemAt(event.pos())
        modifiers = event.modifiers()

        if not clicked_item:
            return super().mousePressEvent(event)

        if modifiers == Qt.ShiftModifier and self.last_selected_item:
            # Perform range selection
            self.selectRange(self.last_selected_item, clicked_item)
            clicked_item.setSelected(clicked_item.isSelected())
            self.last_selected_item = clicked_item
        elif modifiers == Qt.ControlModifier:
            # Toggle the selection state of the clicked item
            clicked_item.setSelected(clicked_item.isSelected())
            # Update the last selected item
            self.last_selected_item = clicked_item
        else:
            # Clear all previous selections and select the clicked item
            self.clearSelection()
            clicked_item.setSelected(clicked_item.isSelected())
            # Update the last selected item
            self.last_selected_item = clicked_item

        # Call the default mousePressEvent for further processing
        super(CustomTreeWidget, self).mousePressEvent(event)

    def selectRange(self, start_item, end_item):
        """
        Select all items between start_item and end_item (inclusive).
        """
        if not start_item or not end_item:
            return

        # Get the indices of the start and end items
        start_index = self.indexFromItem(start_item).row()
        end_index = self.indexFromItem(end_item).row()

        # Ensure proper range direction (start to end)
        if start_index > end_index:
            start_index, end_index = end_index, start_index

        # Iterate through items in the range and select them
        for i in range(start_index, end_index):
            item = self.topLevelItem(i)
            if item:
                item.setSelected(True)

    def clearSelection(self):
        super().clearSelection()
        self.last_selected_item = None
