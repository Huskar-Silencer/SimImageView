"""Main window for the image viewer application"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QMenuBar, QToolBar, QStatusBar, QFileDialog, QProgressBar, QMessageBox, QDialog
)
from PySide6.QtGui import QPixmap, QIcon, QAction, QKeySequence
from PySide6.QtCore import Qt, QSize, QTimer
from pathlib import Path
import logging
import os

from ui.image_viewer import ImageViewerWidget
from utils.image_handler import ImageHandler
from utils.constants import APP_TITLE, APP_VERSION

logger = logging.getLogger(__name__)


class ImagePropertiesDialog(QDialog):
    """Dialog to display image properties"""
    
    def __init__(self, parent, file_path, pixmap):
        super().__init__(parent)
        self.setWindowTitle("Image Properties")
        self.setGeometry(100, 100, 400, 300)
        self.setup_ui(file_path, pixmap)
    
    def setup_ui(self, file_path, pixmap):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Get file information
        file_path = Path(file_path)
        file_size = file_path.stat().st_size
        file_size_str = self.format_file_size(file_size)
        
        # Get image information
        img_width = pixmap.width()
        img_height = pixmap.height()
        img_format = pixmap.format()
        
        # Create labels
        properties = [
            ("File Name:", file_path.name),
            ("File Path:", str(file_path)),
            ("File Size:", file_size_str),
            ("Image Width:", f"{img_width} px"),
            ("Image Height:", f"{img_height} px"),
            ("Dimensions:", f"{img_width} × {img_height}"),
            ("Format:", self.format_to_string(img_format)),
            ("File Type:", file_path.suffix.upper()),
        ]
        
        for label_text, value_text in properties:
            row_layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold; min-width: 100px;")
            value = QLabel(value_text)
            value.setWordWrap(True)
            row_layout.addWidget(label)
            row_layout.addWidget(value)
            layout.addLayout(row_layout)
        
        layout.addStretch()
        
        # Close button
        close_button = self.buttonBox = QMessageBox()
        close_button = QMessageBox()
    
    @staticmethod
    def format_file_size(size_bytes):
        """Format file size to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    @staticmethod
    def format_to_string(img_format):
        """Convert QImage format to string"""
        format_map = {
            0: "Invalid",
            1: "Mono",
            2: "MonoLSB",
            3: "Indexed8",
            4: "RGB32",
            5: "ARGB32",
            6: "ARGB32_Premultiplied",
            7: "RGB16",
            8: "ARGB8565_Premultiplied",
            9: "RGB666",
            10: "ARGB6666_Premultiplied",
            11: "RGB555",
            12: "ARGB8555_Premultiplied",
            13: "RGB888",
            14: "RGB444",
            15: "ARGB4444_Premultiplied",
            16: "RGBX8888",
            17: "RGBA8888",
            18: "RGBA8888_Premultiplied",
            19: "BGR30",
            20: "A2BGR30_Premultiplied",
            21: "RGB30",
            22: "A2RGB30_Premultiplied",
            23: "Alpha8",
            24: "Grayscale8",
            25: "RGBX64",
            26: "RGBA64",
            27: "RGBA64_Premultiplied",
            28: "Grayscale16",
            29: "BGR888",
        }
        return format_map.get(int(img_format), "Unknown")


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.image_handler = ImageHandler()
        self.current_file = None
        self.current_pixmap = None
        self.image_list = []
        self.current_index = 0

        self.setup_ui()
        self.setup_menu_bar()
        self.setup_tool_bar()
        self.setup_status_bar()
        self.connect_signals()

    def setup_ui(self):
        """Initialize user interface"""
        self.setWindowTitle(f"{APP_TITLE} v{APP_VERSION}")
        self.setWindowIcon(QIcon("resources/app_icon.png"))
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(self.get_stylesheet())

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Image viewer
        self.image_viewer = ImageViewerWidget()
        layout.addWidget(self.image_viewer)

    def setup_menu_bar(self):
        """Create menu bar with File, Edit, View, and Help menus"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.setStatusTip("Open an image file")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        open_folder_action = QAction("Open Folder", self)
        open_folder_action.setShortcut("Ctrl+Shift+O")
        open_folder_action.setStatusTip("Open a folder containing images")
        open_folder_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_folder_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")

        copy_action = QAction("Copy", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.setStatusTip("Copy current image")
        copy_action.triggered.connect(self.copy_image)
        edit_menu.addAction(copy_action)

        # View menu
        view_menu = menubar.addMenu("View")

        fit_window_action = QAction("Fit to Window", self)
        fit_window_action.setShortcut("F")
        fit_window_action.setStatusTip("Fit image to window")
        fit_window_action.triggered.connect(self.fit_to_window)
        view_menu.addAction(fit_window_action)

        actual_size_action = QAction("Actual Size", self)
        actual_size_action.setShortcut("Ctrl+0")
        actual_size_action.setStatusTip("Show image at actual size")
        actual_size_action.triggered.connect(self.actual_size)
        view_menu.addAction(actual_size_action)

        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        zoom_in_action.setStatusTip("Zoom in")
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        zoom_out_action.setStatusTip("Zoom out")
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)

        view_menu.addSeparator()

        rotate_left_action = QAction("Rotate Left", self)
        rotate_left_action.setShortcut("Home")
        rotate_left_action.setStatusTip("Rotate image left")
        rotate_left_action.triggered.connect(self.rotate_left)
        view_menu.addAction(rotate_left_action)

        rotate_right_action = QAction("Rotate Right", self)
        rotate_right_action.setShortcut("End")
        rotate_right_action.setStatusTip("Rotate image right")
        rotate_right_action.triggered.connect(self.rotate_right)
        view_menu.addAction(rotate_right_action)

        view_menu.addSeparator()

        properties_action = QAction("Image Properties", self)
        properties_action.setShortcut("Ctrl+I")
        properties_action.setStatusTip("Show image properties")
        properties_action.triggered.connect(self.show_properties)
        view_menu.addAction(properties_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.setStatusTip("About this application")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_tool_bar(self):
        """Create toolbar with common actions"""
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))

        # Navigation buttons
        prev_action = QAction("Previous", self)
        prev_action.setShortcut("Page_Up")
        prev_action.setStatusTip("Previous image (Page Up)")
        prev_action.triggered.connect(self.previous_image)
        toolbar.addAction(prev_action)

        next_action = QAction("Next", self)
        next_action.setShortcut("Page_Down")
        next_action.setStatusTip("Next image (Page Down)")
        next_action.triggered.connect(self.next_image)
        toolbar.addAction(next_action)

        toolbar.addSeparator()

        # Zoom buttons
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)

        fit_window_action = QAction("Fit Window", self)
        fit_window_action.triggered.connect(self.fit_to_window)
        toolbar.addAction(fit_window_action)

        toolbar.addSeparator()

        # Properties button
        properties_action = QAction("Properties", self)
        properties_action.setShortcut("Ctrl+I")
        properties_action.setStatusTip("Show image properties (Ctrl+I)")
        properties_action.triggered.connect(self.show_properties)
        toolbar.addAction(properties_action)

    def setup_status_bar(self):
        """Create status bar"""
        self.status_label = QLabel("Ready")
        self.statusBar().addWidget(self.status_label, 1)

        self.info_label = QLabel("")
        self.statusBar().addPermanentWidget(self.info_label)

    def connect_signals(self):
        """Connect signals to slots"""
        self.image_viewer.image_dropped.connect(self.open_dropped_file)

    def open_file(self):
        """Open a single image file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Image Files (*.jpg *.jpeg *.png *.bmp *.gif *.webp);;All Files (*)"
        )

        if file_path:
            # When opening a single file, create a list with just that file
            folder_path = str(Path(file_path).parent)
            self.image_list = self.image_handler.get_images_from_folder(folder_path)
            
            # Find the current file index
            if self.image_list and file_path in self.image_list:
                self.current_index = self.image_list.index(file_path)
            else:
                self.image_list = [file_path]
                self.current_index = 0
            
            self.load_image(file_path)

    def open_folder(self):
        """Open all images from a folder"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Open Folder"
        )

        if folder_path:
            self.image_list = self.image_handler.get_images_from_folder(folder_path)
            if self.image_list:
                self.current_index = 0
                self.load_image(self.image_list[0])
                self.update_status()
            else:
                self.status_label.setText("No images found in this folder")

    def load_image(self, file_path):
        """Load and display an image"""
        try:
            pixmap = self.image_handler.load_image(file_path)
            if pixmap:
                self.image_viewer.set_image(pixmap)
                self.current_file = file_path
                self.current_pixmap = pixmap
                self.update_status()
            else:
                self.status_label.setText(f"Failed to load image: {file_path}")
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            logger.exception(f"Failed to load image: {file_path}")

    def open_dropped_file(self, file_path):
        """Handle dropped file"""
        # When a file is dropped, treat it like opening a single file
        folder_path = str(Path(file_path).parent)
        self.image_list = self.image_handler.get_images_from_folder(folder_path)
        
        if self.image_list and file_path in self.image_list:
            self.current_index = self.image_list.index(file_path)
        else:
            self.image_list = [file_path]
            self.current_index = 0
        
        self.load_image(file_path)

    def copy_image(self):
        """Copy current image to clipboard"""
        if self.current_file:
            self.image_viewer.copy_to_clipboard()
            self.status_label.setText("Image copied to clipboard")

    def fit_to_window(self):
        """Fit image to window"""
        self.image_viewer.fit_to_window()

    def actual_size(self):
        """Show image at actual size"""
        self.image_viewer.set_zoom(1.0)

    def zoom_in(self):
        """Zoom in"""
        self.image_viewer.zoom_in()

    def zoom_out(self):
        """Zoom out"""
        self.image_viewer.zoom_out()

    def rotate_left(self):
        """Rotate image left"""
        self.image_viewer.rotate(-90)

    def rotate_right(self):
        """Rotate image right"""
        self.image_viewer.rotate(90)

    def previous_image(self):
        """Show previous image"""
        if not self.image_list:
            self.status_label.setText("No images loaded")
            return
        
        if self.current_index > 0:
            self.current_index -= 1
            self.load_image(self.image_list[self.current_index])
        else:
            self.status_label.setText("Already at the first image")

    def next_image(self):
        """Show next image"""
        if not self.image_list:
            self.status_label.setText("No images loaded")
            return
        
        if self.current_index < len(self.image_list) - 1:
            self.current_index += 1
            self.load_image(self.image_list[self.current_index])
        else:
            self.status_label.setText("Already at the last image")

    def update_status(self):
        """Update status bar information"""
        if self.current_file:
            file_name = Path(self.current_file).name
            if self.image_list:
                info = f"{file_name} ({self.current_index + 1}/{len(self.image_list)})"
            else:
                info = file_name
            self.info_label.setText(info)

    def show_properties(self):
        """Show image properties dialog"""
        if not self.current_file or not self.current_pixmap:
            QMessageBox.warning(self, "Warning", "No image loaded")
            return
        
        dialog = ImagePropertiesDialog(self, self.current_file, self.current_pixmap)
        dialog.exec()

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About SimImageView",
            f"{APP_TITLE} v{APP_VERSION}\n\nA simple image viewer built with PySide6"
        )

    def get_stylesheet(self):
        """Get application stylesheet"""
        return """
            QMainWindow {
                background-color: #f0f0f0;
            }
            QMenuBar {
                background-color: #ffffff;
                border-bottom: 1px solid #e0e0e0;
            }
            QToolBar {
                background-color: #ffffff;
                border-bottom: 1px solid #e0e0e0;
                spacing: 5px;
            }
            QStatusBar {
                background-color: #ffffff;
                border-top: 1px solid #e0e0e0;
            }
            QDialog {
                background-color: #f5f5f5;
            }
        """
